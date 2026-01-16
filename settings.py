import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp_files")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
FONTS_DIR = os.path.join(BASE_DIR, "fonts") # Ensure you have fonts here if not system installed

# Drive Config
DRIVE_FOLDER_ID = "1lil9WjBv1yutMHl9YrTyUyIhVKnrCgv3"

# Ensure directories exist
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

# Styles
STYLE_BOLD_REEL = "The Bold Reel"
STYLE_MINIMALIST = "Minimalist"
STYLE_DYNAMIC_POP = "Dynamic Pop"

STYLES = [STYLE_BOLD_REEL, STYLE_MINIMALIST, STYLE_DYNAMIC_POP]

# Fonts (System fonts or local paths)
FONT_BOLD = os.path.join(FONTS_DIR, "Roboto-Bold.ttf")
FONT_MINIMAL = os.path.join(FONTS_DIR, "Roboto-Regular.ttf")
FONT_IMPACT = os.path.join(FONTS_DIR, "Anton-Regular.ttf")

# AI Models
WHISPER_MODEL_SIZE = "medium"

# Video
VIDEO_HEIGHT_VERTICAL = 1920
VIDEO_WIDTH_VERTICAL = 1080
