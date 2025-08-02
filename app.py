import os
import json
import logging
from datetime import timedelta
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session, send_file, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_caching import Cache
import database
import request_handler as rh
from media_scanner import start_media_scanner, get_library_movies, get_library_tv_shows, get_movie_details_by_id, get_tv_show_details_by_id, scan_and_update_library
import tracker_manager

# --- Logging and App Initialization ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# --- Caching Configuration ---
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# --- Configuration Management ---
CONFIG_FILE = 'config.json'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        logging.warning("config.json not found. Creating a new one.")
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"TMDB_API_KEY": "", "MOVIE_DIR": "", "TV_DIR": ""}, f, indent=4)
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

config = load_config()
app.config.update(config)

# --- User Authentication ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password, role='user'):
        self.id = id
        self.username = username
        self.password = password
        self.role = role

    def is_admin(self):
        return self.role == 'admin'

@login_manager.user_loader
def load_user(user_id):
    user_data = database.get_user_by_id(user_id)
    if user_data:
        return User(user_data['id'], user_data['username'], user_data['password'], user_data['role'])
    return None

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function

# --- Initialization ---
with app.app_context():
    database.init_db()
    start_media_scanner(app)

# --- Main Routes ---
@app.route('/')
@login_required
def index():
    return render_template('index.html',
                           recent_movies=get_library_movies(sort_by='added', limit=12),
                           recent_tv=get_library_tv_shows(sort_by='added', limit=12))

# ... (login, signup, logout routes remain the same) ...

# --- Control Panel (Admin Only) ---
@app.route('/control')
@admin_required
def control_panel():
    return render_template('control.html')

@app.route('/control/settings', methods=['GET', 'POST'])
@admin_required
def control_settings():
    if request.method == 'POST':
        # Save general config
        config['TMDB_API_KEY'] = request.form.get('tmdb_api_key')
        config['MOVIE_DIR'] = request.form.get('movie_dir')
        config['TV_DIR'] = request.form.get('tv_dir')
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        
        # Save Prowlarr config
        prowlarr_config = tracker_manager.load_prowlarr_config() or configparser.ConfigParser()
        if 'Prowlarr' not in prowlarr_config: prowlarr_config.add_section('Prowlarr')
        prowlarr_config.set('Prowlarr', 'url', request.form.get('prowlarr_url'))
        prowlarr_config.set('Prowlarr', 'api_key', request.form.get('prowlarr_api_key'))
        tracker_manager.save_config(prowlarr_config, tracker_manager.PROWLARR_CONFIG_FILE)

        # Save BTN config
        btn_config = tracker_manager.load_btn_config() or configparser.ConfigParser()
        if 'BTN' not in btn_config: btn_config.add_section('BTN')
        btn_config.set('BTN', 'api_key', request.form.get('btn_api_key'))
        tracker_manager.save_config(btn_config, tracker_manager.BTN_CONFIG_FILE)

        # Save PTP config
        ptp_config = tracker_manager.load_ptp_config() or configparser.ConfigParser()
        if 'PTP' not in ptp_config: ptp_config.add_section('PTP')
        ptp_config.set('PTP', 'api_key', request.form.get('ptp_api_key'))
        ptp_config.set('PTP', 'passkey', request.form.get('ptp_passkey'))
        tracker_manager.save_config(ptp_config, tracker_manager.PTP_CONFIG_FILE)
        
        flash('Settings saved successfully!')
        return redirect(url_for('control_settings'))

    prowlarr_conf = tracker_manager.load_prowlarr_config()
    btn_conf = tracker_manager.load_btn_config()
    ptp_conf = tracker_manager.load_ptp_config()
    
    return render_template('settings.html', 
                           config=config, 
                           prowlarr_conf=prowlarr_conf,
                           btn_conf=btn_conf,
                           ptp_conf=ptp_conf)

# --- Statistics (Admin Only) ---
@app.route('/statistics')
@admin_required
def statistics_page():
    stats = {
        'most_watched': database.get_most_watched_media(),
        'library_growth': database.get_library_growth(),
        'playback_history': database.get_playback_history()
    }
    return render_template('statistics.html', stats=stats)

# ... (other routes like search, libraries, details, player remain the same) ...

@app.route('/requests')
@login_required
def requests_page():
    return render_template('requests.html', requests=rh.load_requests())

