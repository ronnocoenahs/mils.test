# api.py
import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from models import Movie, Show, SearchResult
from tracker_manager import load_trackers_config
from watchlist_manager import load_watchlist, save_watchlist

# A simple script to handle all core logic for search and watchlist management.

def parse_torznab_xml(xml_content):
    """Parses a Torznab-style XML response and extracts torrent data."""
    results = []
    try:
        root = ET.fromstring(xml_content)
        channel = root.find("channel")
        for item in channel.findall("item"):
            title = item.find("title").text
            link = item.find("link").text
            size = None
            seeders = None
            
            for attr in item.findall("{http://torznab.com/schemas/2015/feed}attr"):
                if attr.attrib['name'] == 'size':
                    size = int(attr.attrib['value'])
                if attr.attrib['name'] == 'seeders':
                    seeders = int(attr.attrib['value'])
            
            if title and link:
                results.append(SearchResult(title, link, size, seeders))
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
    return results

def parse_html_response(html_content, tracker_name):
    """
    Simulates parsing an HTML page. This is a simple example for demonstration.
    Real-world scraping requires specific CSS selectors for each tracker.
    """
    results = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # This is a mock-up. A real implementation would need to be tailored.
    for row in soup.find_all('tr', class_='torrent-row'):
        title_tag = row.find('a', class_='torrent-title')
        size_tag = row.find('span', class_='torrent-size')
        seed_tag = row.find('span', class_='torrent-seeders')
        
        if title_tag and size_tag and seed_tag:
            results.append(SearchResult(
                title_tag.text.strip(),
                'mock_link', # Real link would be parsed from HTML
                size_tag.text.strip(),
                int(seed_tag.text.strip())
            ))
    return results

def _perform_search_sync(tracker_config, query_data):
    """
    Performs a search on a single tracker with enhanced logic for
    authentication and parsing. This is a synchronous helper function.
    """
    tracker_name = tracker_config.get('name', 'Unknown')
    base_url = tracker_config.get('base_url')
    auth_type = tracker_config.get('auth_type', 'none')
    parser_type = tracker_config.get('parser', 'torznab_xml')

    if not base_url:
        return []

    session = requests.Session()
    
    try:
        # --- Authentication Logic ---
        if auth_type == "cookies":
            auth_url = tracker_config.get("auth_url")
            login_data = tracker_config.get("login_data")
            if auth_url and login_data:
                session.post(auth_url, data=login_data)
        elif auth_type == "http_basic":
            username = tracker_config.get("username")
            password = tracker_config.get("password")
            if username and password:
                session.auth = HTTPBasicAuth(username, password)
        
        # --- Search Parameters ---
        params_map = tracker_config.get("params", {})
        search_params = {
            params_map.get("q", "q"): query_data["query"],
            params_map.get("t", "t"): query_data["type"]
        }
        
        if query_data.get("categories"):
            search_params[params_map.get("cat", "cat")] = ",".join(query_data["categories"])
        if query_data.get("min_seeders"):
            search_params[params_map.get("min_seeders", "min_seeders")] = query_data["min_seeders"]
        
        if auth_type == "api_key":
            api_key = tracker_config.get("api_key")
            search_params[params_map.get("apikey", "apikey")] = api_key

        # --- Perform the search ---
        response = session.get(base_url, params=search_params, timeout=15)
        response.raise_for_status()
        
        # --- Parsing Logic ---
        if parser_type == "torznab_xml":
            results = parse_torznab_xml(response.text)
        elif parser_type == "html":
            # Mock-up HTML response for demonstration
            mock_html = f"""
            <html><body>
            <h1>Search Results for {query_data['query']} from {tracker_name}</h1>
            <table>
            <tr class="torrent-row"><td><a class="torrent-title">Result 1</a></td><td><span class="torrent-size">2.1 GB</span></td><td><span class="torrent-seeders">100</span></td></tr>
            <tr class="torrent-row"><td><a class="torrent-title">Result 2</a></td><td><span class="torrent-size">4.5 GB</span></td><td><span class="torrent-seeders">50</span></td></tr>
            </table>
            </body></html>
            """
            results = parse_html_response(mock_html, tracker_name)
        else:
            results = []
        return results

    except requests.exceptions.RequestException as e:
        print(f"Error searching {tracker_name}: {e}")
        return []
    finally:
        session.close()

async def find_best_release(query_data):
    """
    Runs a parallel search across all configured trackers and returns
    the best result based on seeders.
    """
    trackers = load_trackers_config()
    if not trackers:
        return None
    
    with ThreadPoolExecutor(max_workers=len(trackers)) as executor:
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(
                executor,
                _perform_search_sync,
                tracker,
                query_data
            )
            for tracker in trackers
        ]
    all_results = await asyncio.gather(*futures)
    
    final_results = []
    for tracker_results in all_results:
        final_results.extend(tracker_results)
    
    if not final_results:
        return None
    
    # Sort by seeders in descending order to find the "best" release
    sorted_results = sorted(final_results, key=lambda x: x.seeders, reverse=True)
    return sorted_results[0]


def get_watchlist():
    """Returns the current watchlist."""
    return load_watchlist()

def add_item_to_watchlist(item_type, title, unique_id=None):
    """Adds a new movie or show to the watchlist."""
    watchlist = load_watchlist()
    if item_type == "movie":
        watchlist["movies"].append(Movie(title, unique_id, False))
    elif item_type == "show":
        watchlist["shows"].append(Show(title, unique_id, False))
    save_watchlist(watchlist)
    print(f"{item_type.capitalize()} '{title}' added to the watchlist.")

def remove_item_from_watchlist(item_type, title):
    """Removes an item from the watchlist."""
    watchlist = load_watchlist()
    if item_type == "movie":
        watchlist["movies"] = [m for m in watchlist["movies"] if m.title.lower() != title.lower()]
    elif item_type == "show":
        watchlist["shows"] = [s for s in watchlist["shows"] if s.title.lower() != title.lower()]
    save_watchlist(watchlist)
    print(f"{item_type.capitalize()} '{title}' removed from the watchlist.")

