import arr_handler
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_all_movies():
    """Retrieves and formats all movies from Radarr."""
    movies = arr_handler.get_all_movies_from_radarr()
    # Add a 'type' field for easier template handling
    for movie in movies:
        movie['type'] = 'movie'
    return movies

def get_all_tv_shows():
    """Retrieves and formats all TV shows from Sonarr."""
    shows = arr_handler.get_all_tv_shows_from_sonarr()
    # Add a 'type' field for easier template handling
    for show in shows:
        show['type'] = 'tv'
    return shows

def get_recently_added_movies(limit=10):
    """Gets the most recently added movies from Radarr."""
    all_movies = get_all_movies()
    # Sort by the 'added' date, descending.
    # The 'added' field is usually in ISO 8601 format.
    try:
        sorted_movies = sorted(all_movies, key=lambda x: x.get('added', ''), reverse=True)
        return sorted_movies[:limit]
    except Exception as e:
        logging.error(f"Could not sort movies by added date: {e}")
        return all_movies[:limit] # Return unsorted slice on error

def get_recently_added_tv(limit=10):
    """Gets the most recently added TV shows from Sonarr."""
    all_shows = get_all_tv_shows()
    # Sort by the 'added' date, descending.
    try:
        sorted_shows = sorted(all_shows, key=lambda x: x.get('added', ''), reverse=True)
        return sorted_shows[:limit]
    except Exception as e:
        logging.error(f"Could not sort TV shows by added date: {e}")
        return all_shows[:limit]

def search_media(query):
    """
    Searches for movies and TV shows in Radarr and Sonarr.
    Note: This performs a library search, not a search for new media.
    """
    if not query:
        return []
        
    all_movies = get_all_movies()
    all_tv_shows = get_all_tv_shows()
    
    results = []
    
    # Search movies
    for movie in all_movies:
        if query.lower() in movie.get('title', '').lower():
            results.append(movie)
            
    # Search TV shows
    for show in all_tv_shows:
        if query.lower() in show.get('title', '').lower():
            results.append(show)
            
    return results

