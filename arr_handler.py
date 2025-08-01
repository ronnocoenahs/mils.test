import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    """Loads the configuration from config.json."""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("config.json not found. Please create it and add your *Arr details.")
        return {}

config = load_config()

# Radarr Configuration
RADARR_URL = config.get('radarr_url')
RADARR_API_KEY = config.get('radarr_api_key')

# Sonarr Configuration
SONARR_URL = config.get('sonarr_url')
SONARR_API_KEY = config.get('sonarr_api_key')

def get_radarr_quality_profiles():
    """Gets all quality profiles from Radarr."""
    if not RADARR_URL or not RADARR_API_KEY:
        return []
    try:
        response = requests.get(f"{RADARR_URL}/api/v3/qualityprofile", params={'apikey': RADARR_API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting Radarr quality profiles: {e}")
        return []

def get_sonarr_quality_profiles():
    """Gets all quality profiles from Sonarr."""
    if not SONARR_URL or not SONARR_API_KEY:
        return []
    try:
        response = requests.get(f"{SONARR_URL}/api/v3/qualityprofile", params={'apikey': SONARR_API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting Sonarr quality profiles: {e}")
        return []

def add_movie_to_radarr(tmdb_id):
    """Adds a movie to Radarr by its TMDB ID."""
    if not RADARR_URL or not RADARR_API_KEY:
        logging.warning("Radarr URL or API Key not configured.")
        return None

    # First, get quality profiles to find a suitable one.
    profiles = get_radarr_quality_profiles()
    if not profiles:
        logging.error("No quality profiles found in Radarr.")
        return None
    # Using the first profile found. This could be made configurable.
    quality_profile_id = profiles[0]['id']
    
    # Assuming the root folder is the first one configured in Radarr.
    # This should be made more robust in a real application.
    root_folder_path = requests.get(f"{RADARR_URL}/api/v3/rootfolder", params={'apikey': RADARR_API_KEY}).json()[0]['path']

    movie_data = {
        'title': f"Movie with TMDB ID: {tmdb_id}", # Placeholder title
        'tmdbId': int(tmdb_id),
        'qualityProfileId': quality_profile_id,
        'rootFolderPath': root_folder_path,
        'addOptions': {
            'searchForMovie': True
        }
    }
    
    try:
        response = requests.post(f"{RADARR_URL}/api/v3/movie", json=movie_data, params={'apikey': RADARR_API_KEY})
        response.raise_for_status()
        logging.info(f"Successfully added movie with TMDB ID {tmdb_id} to Radarr.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error adding movie to Radarr: {e}")
        return None

def add_show_to_sonarr(tvdb_id):
    """Adds a TV show to Sonarr by its TVDB ID."""
    if not SONARR_URL or not SONARR_API_KEY:
        logging.warning("Sonarr URL or API Key not configured.")
        return None

    profiles = get_sonarr_quality_profiles()
    if not profiles:
        logging.error("No quality profiles found in Sonarr.")
        return None
    quality_profile_id = profiles[0]['id']
    
    root_folder_path = requests.get(f"{SONARR_URL}/api/v3/rootfolder", params={'apikey': SONARR_API_KEY}).json()[0]['path']

    show_data = {
        'title': f"Show with TVDB ID: {tvdb_id}", # Placeholder
        'tvdbId': int(tvdb_id),
        'qualityProfileId': quality_profile_id,
        'rootFolderPath': root_folder_path,
        'addOptions': {
            'searchForMissingEpisodes': True
        }
    }

    try:
        response = requests.post(f"{SONARR_URL}/api/v3/series", json=show_data, params={'apikey': SONARR_API_KEY})
        response.raise_for_status()
        logging.info(f"Successfully added show with TVDB ID {tvdb_id} to Sonarr.")
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error adding show to Sonarr: {e}")
        return None

def get_all_movies_from_radarr():
    """Retrieves all movies from the Radarr library."""
    if not RADARR_URL or not RADARR_API_KEY:
        return []
    try:
        response = requests.get(f"{RADARR_URL}/api/v3/movie", params={'apikey': RADARR_API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting movies from Radarr: {e}")
        return []

def get_all_tv_shows_from_sonarr():
    """Retrieves all TV shows from the Sonarr library."""
    if not SONARR_URL or not SONARR_API_KEY:
        return []
    try:
        response = requests.get(f"{SONARR_URL}/api/v3/series", params={'apikey': SONARR_API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error getting TV shows from Sonarr: {e}")
        return []

def get_movie(movie_id):
    """Gets details for a single movie from Radarr."""
    if not RADARR_URL or not RADARR_API_KEY:
        return None
    try:
        url = f"{RADARR_URL}/api/v3/movie/{movie_id}"
        response = requests.get(url, params={'apikey': RADARR_API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching movie details from Radarr: {e}")
        return None

def get_tv_show_details(series_id):
    """Gets details for a single TV show from Sonarr."""
    if not SONARR_URL or not SONARR_API_KEY:
        return None
    try:
        url = f"{SONARR_URL}/api/v3/series/{series_id}"
        response = requests.get(url, params={'apikey': SONARR_API_KEY})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching TV show details from Sonarr: {e}")
        return None

def get_tv_show_episodes(series_id):
    """Gets all episodes for a given series ID from Sonarr."""
    if not SONARR_URL or not SONARR_API_KEY:
        return []
    try:
        url = f"{SONARR_URL}/api/v3/episode"
        params = {'apikey': SONARR_API_KEY, 'seriesId': series_id}
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching episodes from Sonarr: {e}")
        return []

def get_episode(episode_id):
    """Gets details for a single episode from Sonarr."""
    if not SONARR_URL or not SONARR_API_KEY:
        logging.warning("Sonarr URL or API key is not configured.")
        return None
    try:
        url = f"{SONARR_URL}/api/v3/episode/{episode_id}?apikey={SONARR_API_KEY}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching episode details from Sonarr: {e}")
        return None

