import configparser
import requests
import xml.etree.ElementTree as ET
import json
import os

# Define the filename for storing requests
REQUESTS_FILE = 'requests.json'

def load_requests():
    """
    Loads requests from the JSON file.
    If the file doesn't exist, it creates a default structure.
    """
    if not os.path.exists(REQUESTS_FILE):
        return {"movies": {"pending": [], "approved": []}, "tv": {"pending": [], "approved": []}}
    with open(REQUESTS_FILE, 'r') as f:
        return json.load(f)

def save_requests(data):
    """
    Saves the given data to the requests JSON file.
    """
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def main():
    """
    Main function to run the all-in-one Jackett-based 'arr' application.
    This script provides a command-line interface to search for and manage
    requests for movies and TV shows.
    """
    # Read configuration from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Jackett configuration
    jackett_host_url = config['jackett']['host_url']
    jackett_api_key = config['jackett']['api_key']

    # Main loop for tab selection
    while True:
        print("\n--- Media Tabs ---")
        print("1. Movies")
        print("2. TV Shows")
        print("3. Exit")
        tab_choice = input("Select a tab (1-3): ")

        if tab_choice == '1':
            handle_tab(jackett_host_url, jackett_api_key, 'movie')
        elif tab_choice == '2':
            handle_tab(jackett_host_url, jackett_api_key, 'tv')
        elif tab_choice == '3':
            break
        else:
            print("Invalid choice. Please try again.")

def handle_tab(host_url, api_key, media_type):
    """
    Handles the user interaction within a specific media tab (Movies or TV).
    
    Args:
        host_url (str): The URL of the Jackett instance.
        api_key (str): The Jackett API key.
        media_type (str): The type of media for this tab ('movie' or 'tv').
    """
    # Determine the correct search type for Jackett API
    search_type = 'movie-search' if media_type == 'movie' else 'tvsearch'
    
    while True:
        print(f"\n--- {media_type.title()} Tab ---")
        print("1. Search for New Content")
        print("2. View Pending Requests")
        print("3. View Approved Requests")
        print("4. Back to Main Menu")
        choice = input("Enter your choice (1-4): ")

        if choice == '1':
            search_and_add_request(host_url, api_key, search_type, media_type)
        elif choice == '2':
            view_requests(media_type, 'pending')
        elif choice == '3':
            view_requests(media_type, 'approved')
        elif choice == '4':
            break
        else:
            print("Invalid choice. Please try again.")

def search_and_add_request(host_url, api_key, search_type, media_type):
    """
    Searches for media and allows the user to make a request.

    Args:
        host_url (str): The URL of your Jackett instance.
        api_key (str): Your Jackett API key.
        search_type (str): The Jackett search category.
        media_type (str): The media type ('movie' or 'tv').
    """
    term = input(f"Enter the {media_type} to search for: ")
    url = f"{host_url}/api/v2.0/indexers/all/results/torznab/api?apikey={api_key}&t={search_type}&q={term}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        items = root.findall('.//item')

        if not items:
            print(f"No results found for '{term}'")
            return

        print("\nSearch results:")
        for i, item in enumerate(items):
            title = item.find('title').text
            print(f"{i + 1}. {title}")
        
        # Allow user to select a result to request
        try:
            req_choice = int(input("\nEnter the number of the item to request (or 0 to cancel): "))
            if req_choice == 0:
                return
            
            selected_item = items[req_choice - 1]
            selected_title = selected_item.find('title').text
            
            # Add to pending requests
            requests_data = load_requests()
            requests_data[media_type + 's']['pending'].append({"title": selected_title})
            save_requests(requests_data)
            
            print(f"'{selected_title}' has been added to pending requests.")

        except (ValueError, IndexError):
            print("Invalid selection.")

    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Jackett: {e}")
    except ET.ParseError:
        print("Error parsing the response from Jackett.")

def view_requests(media_type, status):
    """
    Displays pending or approved requests and allows for approval of pending items.
    
    Args:
        media_type (str): The type of media ('movie' or 'tv').
        status (str): The status of requests to view ('pending' or 'approved').
    """
    requests_data = load_requests()
    items = requests_data[media_type + 's'][status]

    print(f"\n--- {status.title()} {media_type.title()} Requests ---")
    if not items:
        print("No requests found.")
        return

    for i, item in enumerate(items):
        print(f"{i + 1}. {item['title']}")

    # If viewing pending requests, give the option to approve them
    if status == 'pending':
        try:
            approve_choice = int(input("\nEnter the number of the item to approve (or 0 to cancel): "))
            if approve_choice == 0:
                return

            item_to_approve = items.pop(approve_choice - 1)
            requests_data[media_type + 's']['approved'].append(item_to_approve)
            save_requests(requests_data)

            print(f"'{item_to_approve['title']}' has been approved.")
            # In a real application, this is where you would trigger the download.

        except (ValueError, IndexError):
            print("Invalid selection.")

# This ensures that the main() function is called only when the script is executed directly.
if __name__ == '__main__':
    main()
