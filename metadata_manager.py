import requests
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_tmdb_config(api_key):
    """Fetches TMDb API configuration, primarily for image base URLs."""
    url = f"https://api.themoviedb.org/3/configuration?api_key={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching TMDb configuration: {e}")
        return None

def get_popular_movies(api_key, limit=20):
    """Fetches a list of popular movies from TMDb."""
    if not api_key:
        logging.warning("TMDb API key is not set. Cannot fetch popular movies.")
        return []
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={api_key}&language=en-US&page=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('results', [])[:limit]
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching popular movies from TMDb: {e}")
        return []

def get_popular_tv_shows(api_key, limit=20):
    """Fetches a list of popular TV shows from TMDb."""
    if not api_key:
        logging.warning("TMDb API key is not set. Cannot fetch popular TV shows.")
        return []
    url = f"https://api.themoviedb.org/3/tv/popular?api_key={api_key}&language=en-US&page=1"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('results', [])[:limit]
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching popular TV shows from TMDb: {e}")
        return []

def get_movie_details(api_key, movie_id):
    """Fetches detailed information for a specific movie."""
    if not api_key:
        return None
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching details for movie ID {movie_id}: {e}")
        return None

def get_tv_show_details(api_key, tv_show_id):
    """Fetches detailed information for a specific TV show."""
    if not api_key:
        return None
    url = f"https://api.themoviedb.org/3/tv/{tv_show_id}?api_key={api_key}&language=en-US"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching details for TV show ID {tv_show_id}: {e}")
        return None

def search_media(api_key, query):
    """Searches for both movies and TV shows on TMDb."""
    if not api_key:
        return []
    url = f"https://api.themoviedb.org/3/search/multi?api_key={api_key}&language=en-US&query={query}&page=1&include_adult=false"
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Filter out people from search results
        results = [item for item in response.json().get('results', []) if item.get('media_type') in ['movie', 'tv']]
        return results
    except requests.exceptions.RequestException as e:
        logging.error(f"Error searching TMDb for query '{query}': {e}")
        return []

