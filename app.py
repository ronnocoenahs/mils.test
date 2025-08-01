import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, send_file
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import arr_handler
import metadata_manager
from database import init_db, get_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a real secret key

# Load configuration
def load_config():
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("config.json not found. Please create it.")
        return {}

app.config.update(load_config())

# --- User Management ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password_hash, role='user'):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    user_data = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if user_data:
        return User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password'], role=user_data['role'])
    return None

def create_initial_user():
    db = get_db()
    if not db.execute('SELECT * FROM users').fetchone():
        username = 'admin'
        # In a real app, prompt for this password or generate it securely
        password = 'password'
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        db.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
                   (username, hashed_password, 'admin'))
        db.commit()
        logging.info(f"Created initial admin user with username: {username} and password: {password}")

@app.before_request
def before_first_request():
    # This function will run before the first request to the application.
    # We check if the 'init_db_done' flag is present in the app context.
    # If not, we initialize the database and set the flag.
    if not hasattr(app, 'init_db_done'):
        init_db()
        create_initial_user()
        app.init_db_done = True


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user_data = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user_data and check_password_hash(user_data['password'], password):
            user = User(id=user_data['id'], username=user_data['username'], password_hash=user_data['password'], role=user_data['role'])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- Main Routes ---

@app.route('/')
@login_required
def index():
    recently_added_movies = metadata_manager.get_recently_added_movies()
    recently_added_tv = metadata_manager.get_recently_added_tv()
    return render_template('index.html', recently_added_movies=recently_added_movies, recently_added_tv=recently_added_tv)

@app.route('/movies')
@login_required
def movies_library():
    all_movies = metadata_manager.get_all_movies()
    return render_template('library_page.html', media_items=all_movies, title="Movies")

@app.route('/tv_shows')
@login_required
def tv_shows_library():
    all_shows = metadata_manager.get_all_tv_shows()
    return render_template('library_page.html', media_items=all_shows, title="TV Shows")

@app.route('/movie/<int:movie_id>')
@login_required
def movie_detail(movie_id):
    movie = arr_handler.get_movie(movie_id)
    if movie:
        return render_template('movie_detail.html', movie=movie)
    return "Movie not found", 404

@app.route('/tv/<int:series_id>')
@login_required
def tv_show_detail(series_id):
    show = arr_handler.get_tv_show_details(series_id)
    episodes_data = arr_handler.get_tv_show_episodes(series_id)
    
    seasons = {}
    if show and episodes_data:
        for episode in episodes_data:
            season_num = episode['seasonNumber']
            if season_num == 0: continue # Skip specials for now
            if season_num not in seasons:
                seasons[season_num] = []
            seasons[season_num].append(episode)
        
        # Sort episodes within each season
        for season_num in seasons:
            seasons[season_num].sort(key=lambda x: x['episodeNumber'])
            
        return render_template('tv_show_detail.html', show=show, seasons=seasons)
    return "TV Show not found", 404

@app.route('/search')
@login_required
def search():
    query = request.args.get('query')
    if not query:
        return redirect(url_for('index'))
    
    search_results = metadata_manager.search_media(query)
    return render_template('search_results.html', results=search_results, query=query)

@app.route('/request_movie', methods=['POST'])
@login_required
def request_movie():
    tmdb_id = request.form['tmdb_id']
    title = request.form['title']
    
    success = arr_handler.add_movie_to_radarr(tmdb_id)
    if success:
        flash(f"'{title}' has been requested successfully!")
    else:
        flash(f"Failed to request '{title}'. Check logs for details.")
    
    return redirect(url_for('movie_detail', movie_id=success.get('id', 0))) if success else redirect(url_for('index'))

@app.route('/request_tv', methods=['POST'])
@login_required
def request_tv():
    tvdb_id = request.form['tvdb_id']
    title = request.form['title']
    
    success = arr_handler.add_show_to_sonarr(tvdb_id)
    if success:
        flash(f"'{title}' has been requested successfully!")
    else:
        flash(f"Failed to request '{title}'. Check logs for details.")
        
    return redirect(url_for('tv_show_detail', series_id=success.get('id', 0))) if success else redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_page():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page.')
        return redirect(url_for('index'))
    config_data = load_config()
    return render_template('admin.html', config=config_data)

@app.route('/admin/save_settings', methods=['POST'])
@login_required
def save_settings():
    if current_user.role != 'admin':
        return jsonify({"success": False, "message": "Unauthorized"}), 403
    
    try:
        with open('config.json', 'r') as f:
            config_data = json.load(f)

        settings = request.get_json()
        
        # Update Jackett settings
        if 'jackett_url' in settings:
            config_data['jackett_url'] = settings['jackett_url']
        if 'jackett_api_key' in settings:
            config_data['jackett_api_key'] = settings['jackett_api_key']

        # Update qBittorrent settings
        if 'qbittorrent_url' in settings:
            config_data['qbittorrent_url'] = settings['qbittorrent_url']
        if 'qbittorrent_user' in settings:
            config_data['qbittorrent_user'] = settings['qbittorrent_user']
        if 'qbittorrent_pass' in settings:
            config_data['qbittorrent_pass'] = settings['qbittorrent_pass']

        with open('config.json', 'w') as f:
            json.dump(config_data, f, indent=4)
        
        # Reload config in dependent modules
        app.config.update(config_data)
        arr_handler.config = arr_handler.load_config()
        arr_handler.SONARR_URL = arr_handler.config.get('sonarr_url')
        arr_handler.SONARR_API_KEY = arr_handler.config.get('sonarr_api_key')
        arr_handler.RADARR_URL = arr_handler.config.get('radarr_url')
        arr_handler.RADARR_API_KEY = arr_handler.config.get('radarr_api_key')

        return jsonify({"success": True, "message": "Settings saved successfully."})

    except Exception as e:
        logging.error(f"Error saving settings: {e}")
        return jsonify({"success": False, "message": "Error saving settings."}), 500

# --- Media Playback Routes ---

@app.route('/player/<string:media_type>/<int:media_id>')
@login_required
def player(media_type, media_id):
    """Renders the player page."""
    if media_type == 'movie':
        stream_url = url_for('stream_movie', movie_id=media_id)
    elif media_type == 'episode':
        # In the tv_show_detail template, we pass episode.id as media_id
        stream_url = url_for('stream_episode', episode_id=media_id)
    else:
        logging.error(f"Invalid media type requested for player: {media_type}")
        return "Invalid media type", 404
        
    return render_template('player.html', stream_url=stream_url)

@app.route('/stream/movie/<int:movie_id>')
@login_required
def stream_movie(movie_id):
    """Streams a movie file."""
    movie = arr_handler.get_movie(movie_id)
    if not movie or not movie.get('hasFile') or 'movieFile' not in movie or 'path' not in movie['movieFile']:
        logging.warning(f"Movie file data not found for movie ID: {movie_id}")
        return "Movie not found or no file available", 404
    
    path = movie['movieFile']['path']
    logging.info(f"Attempting to stream movie from path: {path}")
    
    try:
        return send_file(path, mimetype='video/mp4', conditional=True)
    except FileNotFoundError:
        logging.error(f"File not found for movie {movie_id} at path: {path}")
        return "File not found on server.", 404
    except Exception as e:
        logging.error(f"Error streaming file for movie {movie_id}: {e}")
        return "Error streaming file", 500

@app.route('/stream/episode/<int:episode_id>')
@login_required
def stream_episode(episode_id):
    """Streams a TV show episode file."""
    episode = arr_handler.get_episode(episode_id)
    if not episode or not episode.get('hasFile') or 'episodeFile' not in episode or 'path' not in episode['episodeFile']:
        logging.warning(f"Episode file data not found for episode ID: {episode_id}")
        return "Episode not found or no file available", 404

    path = episode['episodeFile']['path']
    logging.info(f"Attempting to stream episode from path: {path}")

    try:
        return send_file(path, mimetype='video/mp4', conditional=True)
    except FileNotFoundError:
        logging.error(f"File not found for episode {episode_id} at path: {path}")
        return "File not found on server.", 404
    except Exception as e:
        logging.error(f"Error streaming file for episode {episode_id}: {e}")
        return "Error streaming file", 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

