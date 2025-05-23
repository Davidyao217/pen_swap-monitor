#!/usr/bin/env python3
"""
Simple script to print all post IDs stored in the seen_posts_shelf database.
"""
import shelve
from config import SEEN_POSTS_SHELVE_FILE

def print_seen_posts():
    """Print all post IDs stored in the seen_posts database."""
    try:
        # Open the shelve file
        with shelve.open(SEEN_POSTS_SHELVE_FILE) as db:
            if not db:
                print("No posts have been stored yet.")
                return
            
            print(f"Found {len(db)} posts in the database:")
            print("-" * 50)
            
            # Print each post ID and construct the Reddit URL
            for post_id in db.keys():
                url = f"https://www.reddit.com/comments/{post_id}"
                print(f"Post ID: {post_id}")
                print(f"URL: {url}")
                print("-" * 50)
                
    except Exception as e:
        print(f"Error accessing the database: {e}")

if __name__ == "__main__":
    print_seen_posts() 