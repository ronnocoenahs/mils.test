import json
import os
import requests
import xml.etree.ElementTree as ET
import logging
import re
from media_scanner import get_tmdb_data

# --- Configuration ---
REQUESTS_FILE = 'requests.json'
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def parse_jackett_item(item):
    """Parses an XML item from Jackett into a dictionary."""
    title = item.find('title').text if item.find('title') is not None else 'N/A'
    year_match = re.search(r'\(?(\d{4})\)?', title)
    year = year_match.group(1) if year_match else None
    clean_title = re.sub(r'\(?\d{4}\)?', '', title).strip()
    clean_title = re.sub(r'[._\s-](S\d{1,2}(E\d{1,2})?|1080p|720p|WEB-DL|BluRay).*', '', clean_title, flags=re.IGNORECASE).strip()
    return {'title': title, 'clean_title': clean_title, 'year': year}

# --- Request File Management ---
def load_requests():
    """Loads requests from the JSON file."""
    if not os.path.exists(REQUESTS_FILE):
        return {"movies": {"pending": [], "approved": []}, "tv": {"pending": [], "approved": []}}
    try:
        with open(REQUESTS_FILE, 'r') as f:
            content = f.read()
            return json.loads(content) if content else {"movies": {"pending": [], "approved": []}, "tv": {"pending": [], "approved": []}}
    except (IOError, json.JSONDecodeError) as e:
        logging.error(f"Error loading requests file: {e}")
        return {"movies": {"pending": [], "approved": []}, "tv": {"pending": [], "approved": []}}

def save_requests(data):
    """Saves data to the requests JSON file."""
    try:
        with open(REQUESTS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        logging.error(f"Error saving requests file: {e}")

# --- Jackett Interaction ---
def search_jackett(url, api_key, query, is_tv=False, limit=None):
    """Searches Jackett and returns structured data."""
    if not all([url, api_key, query]): return []
    params = {'apikey': api_key, 't': 'search', 'q': query, 'cat': '5000' if is_tv else '2000'}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        results = [parse_jackett_item(item) for item in items]
        return results[:limit] if limit else results
    except (requests.RequestException, ET.ParseError) as e:
        logging.error(f"Error with Jackett search: {e}")
        return []

def get_recent_from_jackett(url, api_key, is_tv=False):
    """Gets the most recent items from a Jackett feed."""
    if not all([url, api_key]): return []
    params = {'apikey': api_key, 't': 'search', 'limit': 10, 'cat': '5000' if is_tv else '2000'}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        return [parse_jackett_item(item) for item in items]
    except (requests.RequestException, ET.ParseError) as e:
        logging.error(f"Error getting recent from Jackett: {e}")
        return []

def enrich_with_tmdb_posters(results, is_tv=False):
    """Adds TMDb poster paths to Jackett results."""
    enriched = []
    for item in results:
        tmdb_info = get_tmdb_data(item['clean_title'], item['year'], is_tv=is_tv)
        if tmdb_info and tmdb_info.get('poster_path'):
            enriched.append({
                'title': item['title'],
                'poster': f"https://image.tmdb.org/t/p/w500{tmdb_info['poster_path']}",
                'year': item['year']
            })
    return enriched

# --- Request Lifecycle Management ---
def add_request(media_type, title, requested_by):
    """Adds a new item to the pending requests list."""
    requests_data = load_requests()
    key = media_type + 's'
    if key not in requests_data: requests_data[key] = {"pending": [], "approved": []}
    
    is_duplicate = any(req['title'].lower() == title.lower() for req in requests_data[key]['pending'] + requests_data[key]['approved'])
    if not is_duplicate:
        requests_data[key]['pending'].append({"title": title, "requested_by": requested_by})
        save_requests(requests_data)
        logging.info(f"Added '{title}' to pending {media_type} requests.")
        return True
    logging.warning(f"Request for '{title}' already exists.")
    return False

def approve_request(media_type, title):
    """Moves a request from pending to approved."""
    requests_data = load_requests()
    key, pending_list = media_type + 's', requests_data.get(media_type + 's', {}).get('pending', [])
    item_to_approve = next((item for item in pending_list if item['title'] == title), None)
    if item_to_approve:
        pending_list.remove(item_to_approve)
        requests_data[key]['approved'].append(item_to_approve)
        save_requests(requests_data)
        logging.info(f"Approved request for '{title}'.")
        return True
    logging.warning(f"Could not find pending request for '{title}' to approve.")
    return False

def deny_request(media_type, title):
    """Removes a request from the pending list."""
    requests_data = load_requests()
    key, pending_list = media_type + 's', requests_data.get(media_type + 's', {}).get('pending', [])
    item_to_deny = next((item for item in pending_list if item['title'] == title), None)
    if item_to_deny:
        pending_list.remove(item_to_deny)
        save_requests(requests_data)
        logging.info(f"Denied request for '{title}'.")
        return True
    logging.warning(f"Could not find pending request for '{title}' to deny.")
    return False

