# watchlist_manager.py
import json
import os
from models import Movie, Show, json_decoder, json_encoder

WATCHLIST_FILE = "watchlist.json"

def load_watchlist(file_path=WATCHLIST_FILE):
    """Loads the watchlist from a JSON file."""
    if not os.path.exists(file_path):
        return {"movies": [], "shows": []}
    try:
        with open(file_path, 'r') as f:
            # Use a custom object hook to convert dictionaries back to objects
            data = json.load(f, object_hook=json_decoder)
            # Ensure the structure is correct, even if the file is empty
            return {
                "movies": [Movie(**m) for m in data.get("movies", [])],
                "shows": [Show(**s) for s in data.get("shows", [])]
            }
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON format in `{file_path}`. Starting with an empty watchlist.")
        return {"movies": [], "shows": []}

def save_watchlist(watchlist, file_path=WATCHLIST_FILE):
    """Saves the watchlist to a JSON file."""
    # Use a custom JSON encoder to handle the custom objects
    with open(file_path, 'w') as f:
        json.dump(watchlist, f, indent=4, default=json_encoder)


