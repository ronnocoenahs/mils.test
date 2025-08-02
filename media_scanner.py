import os
import sqlite3
import time
import logging
import json
import uuid
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
import re
from threading import Thread

# --- Configuration ---
DB_NAME = 'slimstash.db'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global Variables ---
app_instance = None
tmdb_api_key = None

# --- Database Interaction ---
def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- Metadata Fetching ---
def get_tmdb_data(query, year=None, is_tv=False):
    """Fetches search results from TMDb."""
    if not tmdb_api_key:
        return None
    search_type = 'tv' if is_tv else 'movie'
    url = f"https://api.themoviedb.org/3/search/{search_type}?api_key={tmdb_api_key}&query={query}"
    if year:
        url += f"&year={year}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json().get('results')
        return results[0] if results else None
    except requests.RequestException as e:
        logging.error(f"Error fetching TMDb data for '{query}': {e}")
        return None

def get_tmdb_details(tmdb_id, is_tv=False):
    """Fetches detailed media information from TMDb by ID."""
    if not tmdb_api_key or not tmdb_id:
        return {}
    media_type = 'tv' if is_tv else 'movie'
    details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={tmdb_api_key}&append_to_response=credits,recommendations"
    try:
        response = requests.get(details_url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching TMDb details for ID {tmdb_id}: {e}")
        return {}

# --- Filename Parsing ---
def parse_filename(filename):
    """Extracts title, year, season, and episode from a filename."""
    filename = os.path.basename(filename)
    title = filename
    year = None
    season = None
    episode = None

    # Year pattern (e.g., 2023)
    year_match = re.search(r'\(?(\d{4})\)?', title)
    if year_match:
        year = int(year_match.group(1))
        title = title.replace(year_match.group(0), '').strip()

    # Season/Episode pattern (e.g., S01E02)
    se_match = re.search(r'[._\s-]([Ss](\d{1,2})[._\s-]*[Ee](\d{1,2}))[._\s-]', title, re.IGNORECASE)
    if se_match:
        season = int(se_match.group(2))
        episode = int(se_match.group(3))
        title = re.split(r'[._\s-][Ss]\d{1,2}[._\s-]*[Ee]\d{1,2}', title, flags=re.IGNORECASE)[0]

    # Clean up title
    title = re.sub(r'\b(1080p|720p|WEB-DL|BluRay|x264|H264|DDP5.1|Atmos|REPACK|PRSRPNT|T3STDRV|Dolf4c3)\b.*', '', title, flags=re.IGNORECASE)
    title = title.replace('.', ' ').replace('_', ' ').strip()
    
    return {'title': title, 'year': year, 'season': season, 'episode': episode}

# --- Library Management ---
def scan_and_update_library():
    """Scans media directories and updates the database."""
    logging.info("Starting library scan...")
    conn = get_db_connection()
    try:
        # We need an app context to access the config
        with app_instance.app_context():
            movie_dir = app_instance.config.get('MOVIE_DIR')
            tv_dir = app_instance.config.get('TV_DIR')

            # Process Movies
            if movie_dir and os.path.exists(movie_dir):
                for root, _, files in os.walk(movie_dir):
                    for file in files:
                        if file.lower().endswith(('.mkv', '.mp4', '.avi')):
                            process_media_file(os.path.join(root, file), conn, is_tv=False)
            
            # Process TV Shows
            if tv_dir and os.path.exists(tv_dir):
                for root, _, files in os.walk(tv_dir):
                    for file in files:
                        if file.lower().endswith(('.mkv', '.mp4', '.avi')):
                            process_media_file(os.path.join(root, file), conn, is_tv=True)
    finally:
        conn.close()
    logging.info("Library scan finished.")

def process_media_file(path, conn, is_tv):
    """Processes a single media file, adding or updating it in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT last_modified FROM movies WHERE path = ? UNION ALL SELECT last_modified FROM tv_shows WHERE path = ?", (path, path))
    result = cursor.fetchone()
    
    current_mtime = os.path.getmtime(path)

    if result and result['last_modified'] == current_mtime:
        return # File hasn't changed

    logging.info(f"Processing new/updated file: {path}")
    parsed = parse_filename(path)
    
    if is_tv:
        # For TV, we group by show title
        tmdb_show_info = get_tmdb_data(parsed['title'], parsed['year'], is_tv=True)
        if not tmdb_show_info: return

        details = get_tmdb_details(tmdb_show_info['id'], is_tv=True)
        if not details: return

        # Get episode-specific details
        episode_details = {}
        if parsed['season'] and parsed['episode']:
            try:
                ep_url = f"https://api.themoviedb.org/3/tv/{details['id']}/season/{parsed['season']}/episode/{parsed['episode']}?api_key={tmdb_api_key}"
                ep_res = requests.get(ep_url).json()
                episode_details['title'] = ep_res.get('name')
                episode_details['overview'] = ep_res.get('overview')
                episode_details['still_path'] = ep_res.get('still_path')
            except Exception:
                pass

        cursor.execute("""
            INSERT OR REPLACE INTO tv_shows (id, title, path, genre, season, episode, episode_title, episode_overview, poster, backdrop_path, overview, release_date, tmdb_id, episode_still_path, last_modified, cast, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), parsed['title'], path, json.dumps([g['name'] for g in details.get('genres', [])]),
            parsed['season'], parsed['episode'], episode_details.get('title'), episode_details.get('overview'),
            f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}",
            f"https://image.tmdb.org/t/p/w1280{details.get('backdrop_path')}",
            details.get('overview'), details.get('first_air_date'), str(details.get('id')),
            f"https://image.tmdb.org/t/p/w300{episode_details.get('still_path')}" if episode_details.get('still_path') else None,
            current_mtime,
            json.dumps([{'name': c['name'], 'character': c['character'], 'profile_path': f"https://image.tmdb.org/t/p/w185{c['profile_path']}" if c['profile_path'] else None} for c in details.get('credits', {}).get('cast', [])[:10]]),
            json.dumps([{'id': r['id'], 'title': r.get('title') or r.get('name'), 'year': (r.get('release_date') or r.get('first_air_date','-')).split('-')[0], 'poster': f"https://image.tmdb.org/t/p/w500{r['poster_path']}", 'type': r['media_type']} for r in details.get('recommendations', {}).get('results', [])[:10]])
        ))
    else: # Movie
        tmdb_movie_info = get_tmdb_data(parsed['title'], parsed['year'])
        if not tmdb_movie_info: return

        details = get_tmdb_details(tmdb_movie_info['id'])
        if not details: return

        cursor.execute("""
            INSERT OR REPLACE INTO movies (id, title, path, genre, year, poster, backdrop_path, overview, release_date, tmdb_id, last_modified, cast, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()), parsed['title'], path, json.dumps([g['name'] for g in details.get('genres', [])]),
            parsed['year'], f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}",
            f"https://image.tmdb.org/t/p/w1280{details.get('backdrop_path')}",
            details.get('overview'), details.get('release_date'), str(details.get('id')), current_mtime,
            json.dumps([{'name': c['name'], 'character': c['character'], 'profile_path': f"https://image.tmdb.org/t/p/w185{c['profile_path']}" if c['profile_path'] else None} for c in details.get('credits', {}).get('cast', [])[:10]]),
            json.dumps([{'id': r['id'], 'title': r.get('title') or r.get('name'), 'year': (r.get('release_date') or r.get('first_air_date','-')).split('-')[0], 'poster': f"https://image.tmdb.org/t/p/w500{r['poster_path']}", 'type': r['media_type']} for r in details.get('recommendations', {}).get('results', [])[:10]])
        ))
    conn.commit()

# --- Library Data Retrieval ---
def get_library_movies(sort_by='title', limit=None):
    conn = get_db_connection()
    order_column = 'last_modified' if sort_by == 'added' else 'title'
    query = f"SELECT DISTINCT title, year, poster, id FROM movies ORDER BY {order_column} DESC"
    if limit:
        query += f" LIMIT {limit}"
    movies = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in movies]

def get_library_tv_shows(sort_by='title', limit=None):
    conn = get_db_connection()
    order_column = 'MAX(last_modified)' if sort_by == 'added' else 'title'
    query = f"SELECT title, release_date, poster, id FROM tv_shows GROUP BY title ORDER BY {order_column} DESC"
    if limit:
        query += f" LIMIT {limit}"
    shows = conn.execute(query).fetchall()
    conn.close()
    return [dict(row) for row in shows]

def get_movie_details_by_id(movie_id):
    conn = get_db_connection()
    movie = conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)).fetchone()
    conn.close()
    return dict(movie) if movie else None

def get_tv_show_details_by_id(show_id):
    conn = get_db_connection()
    show_episode = conn.execute("SELECT * FROM tv_shows WHERE id = ?", (show_id,)).fetchone()
    if not show_episode:
        conn.close()
        return None
    
    all_episodes = conn.execute("SELECT * FROM tv_shows WHERE title = ? ORDER BY season, episode", (show_episode['title'],)).fetchall()
    conn.close()

    show_dict = dict(show_episode)
    show_dict['seasons'] = {}
    for ep in all_episodes:
        s_num = ep['season']
        if s_num not in show_dict['seasons']:
            show_dict['seasons'][s_num] = []
        show_dict['seasons'][s_num].append(dict(ep))
    
    return show_dict

# --- Filesystem Monitoring ---
class MediaChangeHandler(FileSystemEventHandler):
    """Handles events from the directory watcher."""
    def on_any_event(self, event):
        if event.is_directory or not any(event.src_path.lower().endswith(ext) for ext in ['.mkv', '.mp4', '.avi']):
            return
        logging.info(f"Detected change: {event.src_path}, event: {event.event_type}")
        scan_and_update_library()

def monitor_directories():
    """Sets up and starts the directory monitoring."""
    event_handler = MediaChangeHandler()
    observer = Observer()
    
    with app_instance.app_context():
        movie_dir = app_instance.config.get('MOVIE_DIR')
        tv_dir = app_instance.config.get('TV_DIR')

        if movie_dir and os.path.exists(movie_dir):
            observer.schedule(event_handler, movie_dir, recursive=True)
        if tv_dir and os.path.exists(tv_dir):
            observer.schedule(event_handler, tv_dir, recursive=True)

    if observer.emitters:
        observer.start()
        logging.info("Started monitoring media directories for changes.")
        try:
            while True:
                time.sleep(3600) # Check less frequently, as real-time is handled by events
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

# --- Main Starter ---
def start_media_scanner(app):
    """Initializes and starts the scanner and monitor in background threads."""
    global app_instance, tmdb_api_key
    app_instance = app
    with app.app_context():
        tmdb_api_key = app.config.get('TMDB_API_KEY')

    # FIX: Run the initial scan in a background thread to prevent blocking
    scan_thread = Thread(target=scan_and_update_library, daemon=True)
    scan_thread.start()

    # Start monitoring in a background thread
    monitor_thread = Thread(target=monitor_directories, daemon=True)
    monitor_thread.start()

