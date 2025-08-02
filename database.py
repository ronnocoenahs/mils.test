import sqlite3
import logging
from werkzeug.security import generate_password_hash
from collections import defaultdict

# --- Configuration ---
DB_NAME = 'slimstash.db'

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_db_connection():
    """Creates and returns a new database connection."""
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        return None

def init_db():
    """Initializes the database, creating tables if they don't exist."""
    conn = get_db_connection()
    if conn is None:
        logging.error("Could not initialize database: connection failed.")
        return

    try:
        with conn:
            cursor = conn.cursor()
            # Users Table with role
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user'
                )
            ''')
            # Add role column if it doesn't exist (for migration)
            try:
                cursor.execute("SELECT role FROM users LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
                cursor.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")

            # Movies Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS movies (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    path TEXT UNIQUE NOT NULL,
                    genre TEXT,
                    year INTEGER,
                    poster TEXT,
                    backdrop_path TEXT,
                    overview TEXT,
                    release_date TEXT,
                    tmdb_id TEXT,
                    last_modified REAL,
                    cast TEXT,
                    recommendations TEXT
                )
            ''')
            # TV Shows Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tv_shows (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    path TEXT UNIQUE NOT NULL,
                    genre TEXT,
                    season INTEGER,
                    episode INTEGER,
                    episode_title TEXT,
                    episode_overview TEXT,
                    poster TEXT,
                    backdrop_path TEXT,
                    overview TEXT,
                    release_date TEXT,
                    tmdb_id TEXT,
                    episode_still_path TEXT,
                    last_modified REAL,
                    cast TEXT,
                    recommendations TEXT
                )
            ''')

            # Playback History Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS playback_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    media_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    watched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Check for and create default admin user
            cursor.execute("SELECT id FROM users WHERE username = ?", ('admin',))
            if cursor.fetchone() is None:
                hashed_password = generate_password_hash('admin')
                cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'admin')", ('admin', hashed_password))
                logging.info("Default 'admin' user created with password 'admin'.")
    except sqlite3.Error as e:
        logging.error(f"Error during database initialization: {e}")
    finally:
        conn.close()

# --- User Management Functions ---

def add_user(username, password):
    """Adds a new user to the database."""
    conn = get_db_connection()
    if conn is None: return False
    try:
        with conn:
            hashed_password = generate_password_hash(password)
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        return True
    except sqlite3.IntegrityError:
        logging.warning(f"Attempted to add duplicate username: {username}")
        return False
    except sqlite3.Error as e:
        logging.error(f"Error adding user '{username}': {e}")
        return False
    finally:
        conn.close()

def get_user_by_id(user_id):
    """Retrieves a user by their ID."""
    conn = get_db_connection()
    if conn is None: return None
    user = None
    try:
        with conn:
            user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.Error as e:
        logging.error(f"Error fetching user by ID {user_id}: {e}")
    finally:
        conn.close()
    return user

def get_user_by_username(username):
    """Retrieves a user by their username."""
    conn = get_db_connection()
    if conn is None: return None
    user = None
    try:
        with conn:
            user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    except sqlite3.Error as e:
        logging.error(f"Error fetching user by username '{username}': {e}")
    finally:
        conn.close()
    return user

def search_library(query):
    """Searches for movies and TV shows in the local database."""
    conn = get_db_connection()
    if conn is None: return []

    results = []
    try:
        with conn:
            movies = conn.execute("SELECT *, 'movie' as type FROM movies WHERE title LIKE ?", ('%' + query + '%',)).fetchall()
            results.extend([dict(row) for row in movies])
            tv_shows = conn.execute("SELECT *, 'tv' as type FROM tv_shows WHERE title LIKE ? GROUP BY title", ('%' + query + '%',)).fetchall()
            results.extend([dict(row) for row in tv_shows])
    except sqlite3.Error as e:
        logging.error(f"Error searching library: {e}")
    finally:
        conn.close()
    return results

# --- Statistics Functions ---

def log_playback(user_id, media_id, media_type):
    """Logs a playback event."""
    conn = get_db_connection()
    if conn is None: return
    try:
        with conn:
            conn.execute("INSERT INTO playback_history (user_id, media_id, media_type) VALUES (?, ?, ?)",
                         (user_id, media_id, media_type))
        logging.info(f"Logged play for user {user_id}, media {media_id}")
    except sqlite3.Error as e:
        logging.error(f"Error logging playback: {e}")
    finally:
        conn.close()

def get_most_watched_media():
    """Gets the most watched movies and TV shows."""
    conn = get_db_connection()
    if conn is None: return []
    query = """
        SELECT
            p.media_id,
            p.media_type,
            COUNT(p.id) as play_count,
            COALESCE(m.title, t.title) as title,
            COALESCE(m.poster, t.poster) as poster
        FROM playback_history p
        LEFT JOIN movies m ON p.media_id = m.id AND p.media_type = 'movie'
        LEFT JOIN tv_shows t ON p.media_id = t.id AND p.media_type = 'tv'
        WHERE title IS NOT NULL
        GROUP BY title, poster
        ORDER BY play_count DESC
        LIMIT 10
    """
    try:
        results = conn.execute(query).fetchall()
        return [dict(row) for row in results]
    except sqlite3.Error as e:
        logging.error(f"Error getting most watched media: {e}")
        return []
    finally:
        conn.close()

def get_library_growth():
    """Gets the number of media items added over time."""
    conn = get_db_connection()
    if conn is None: return {}

    growth_data = defaultdict(int)
    try:
        # Movies
        movie_growth = conn.execute("SELECT strftime('%Y-%m', last_modified, 'unixepoch') as month, COUNT(*) as count FROM movies GROUP BY month ORDER BY month").fetchall()
        for row in movie_growth:
            growth_data[row['month']] += row['count']

        # TV Shows (count unique shows per month)
        tv_growth = conn.execute("SELECT strftime('%Y-%m', last_modified, 'unixepoch') as month, COUNT(DISTINCT title) as count FROM tv_shows GROUP BY month ORDER BY month").fetchall()
        for row in tv_growth:
            growth_data[row['month']] += row['count']

        # Sort and format for the chart
        sorted_growth = sorted(growth_data.items())
        return {
            "labels": [item[0] for item in sorted_growth],
            "data": [item[1] for item in sorted_growth]
        }
    except sqlite3.Error as e:
        logging.error(f"Error getting library growth: {e}")
        return {}
    finally:
        conn.close()

def get_playback_history():
    """Gets the recent playback history."""
    conn = get_db_connection()
    if conn is None: return []
    query = """
        SELECT
            p.watched_at,
            u.username,
            p.media_type,
            COALESCE(m.title, t.title) as title,
            t.season,
            t.episode
        FROM playback_history p
        JOIN users u ON p.user_id = u.id
        LEFT JOIN movies m ON p.media_id = m.id AND p.media_type = 'movie'
        LEFT JOIN tv_shows t ON p.media_id = t.id AND p.media_type = 'tv'
        WHERE title IS NOT NULL
        ORDER BY p.watched_at DESC
        LIMIT 20
    """
    try:
        results = conn.execute(query).fetchall()
        return [dict(row) for row in results]
    except sqlite3.Error as e:
        logging.error(f"Error getting playback history: {e}")
        return []
    finally:
        conn.close()

