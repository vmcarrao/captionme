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
        
        # Integrity Check
        if os.path.getsize(save_path) < 1000: # 1KB minimum
            print(f"Warning: File {save_path} is too small. Deleting.")
            os.remove(save_path)
            return False
            
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        if os.path.exists(save_path):
             os.remove(save_path)
        return False


def fetch_google_font(font_name: str) -> str:
    """
    Attempts to download a Google Font by name (e.g. "Lobster", "Open Sans").
    Returns the local path to the .ttf file if successful, or None.
    """
    # Clean name
    clean_name = font_name.strip()
    file_name = f"{clean_name.replace(' ', '')}-Regular.ttf"
    save_path = os.path.join(FONTS_DIR, file_name)
    
    if os.path.exists(save_path):
        return save_path
        
    # Google Fonts GitHub structure isn't perfectly uniform, usually:
    # ofl/fontname/FontName-Regular.ttf
    # apache/fontname/FontName-Regular.ttf
    # ufl/fontname/FontName-Regular.ttf
    
    os.makedirs(FONTS_DIR, exist_ok=True)
    
    base_urls = [
        f"https://github.com/google/fonts/raw/main/ofl/{clean_name.lower().replace(' ', '')}/{file_name}",
        f"https://github.com/google/fonts/raw/main/apache/{clean_name.lower().replace(' ', '')}/{file_name}",
        f"https://github.com/google/fonts/raw/main/ufl/{clean_name.lower().replace(' ', '')}/{file_name}"
    ]
    
    for url in base_urls:
        if download_file(url, save_path):
            return save_path
            
    return None

def download_google_fonts():
    """
    Downloads required base Google Fonts if they don't exist locally.
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
            print(f"Downloading font: {filename}...")
            if download_file(url, file_path):
                created += 1
        else:
            pass
            
    return created

