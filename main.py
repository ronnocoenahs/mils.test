# main.py
import asyncio
from api import find_best_release, add_item_to_watchlist, remove_item_from_watchlist, get_watchlist

async def main():
    """
    Example of how a main application would interact with the API.
    """
    print("--- Example: Adding a movie to the watchlist ---")
    add_item_to_watchlist("movie", "Blade Runner 2049", "tt1856101")
    
    print("\n--- Example: Performing a one-time search ---")
    query_data = {
        "query": "Blade Runner 2049",
        "type": "movie",
        "categories": [],
        "min_seeders": "10"
    }
    best_release = await find_best_release(query_data)
    if best_release:
        print(f"Found best release: {best_release.title} with {best_release.seeders} seeders.")
    else:
        print("No results found.")

    print("\n--- Example: Getting the current watchlist ---")
    watchlist = get_watchlist()
    for movie in watchlist["movies"]:
        print(f"Movie: {movie.title}, Downloaded: {movie.downloaded}")

if __name__ == "__main__":
    asyncio.run(main())

