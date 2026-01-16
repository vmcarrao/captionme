import os
import requests
import streamlit as st
from settings import FONTS_DIR

def download_file(url, save_path):
    """Downloads a file from a URL to a specific path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def download_google_fonts():
    """
    Downloads required Google Fonts if they don't exist locally.
    """
    # Define fonts to download (Raw GitHub URLs for Google Fonts)
    fonts = {
        "Anton-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf",
        "Roboto-Regular.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf",
        "Roboto-Bold.ttf": "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Bold.ttf"
    }
    
    os.makedirs(FONTS_DIR, exist_ok=True)
    
    created = 0
    for filename, url in fonts.items():
        file_path = os.path.join(FONTS_DIR, filename)
        if not os.path.exists(file_path):
            # st.write(f"Downloading font: {filename}...") # Debug info usually not needed in UI unless slow
            print(f"Downloading font: {filename}...")
            if download_file(url, file_path):
                created += 1
        else:
            pass
            # print(f"Font already exists: {filename}")
            
    return created
