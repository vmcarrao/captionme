#!/bin/bash

# 1. Install System Dependencies via Homebrew
echo "Installing system dependencies..."
brew install ffmpeg imagemagick ghostscript

# 2. Setup Python Virtual Environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# 3. Upgrade Pip and Install Requirements
echo "Installing Python packages..."
pip install --upgrade pip
pip install streamlit faster-whisper "moviepy<2.0.0" google-api-python-client \
            google-auth-oauthlib google-auth-httplib2 pandas watchdog

echo "------------------------------------------------"
echo "Setup Complete!"
echo "To start the app, run: source venv/bin/activate && streamlit run app.py"
echo "------------------------------------------------"

### 📋 Usage Instructions
    # Save the file: Save the code above as setup.sh in your project folder.

    # Make it executable: Open your Terminal and run chmod +x setup.sh.
    # Run the script: Type ./setup.sh to start the installation.

    # Activate & Launch: Every time you want to work on the app, run source venv/bin/activate followed by streamlit run app.py.

    # ⚠️ Apple Silicon (M2) Considerations
    # Performance: The script uses faster-whisper, which is optimized for CPU execution on Apple Silicon using int8 quantization for high speed.

    # Pathing: On macOS Tahoe, Homebrew installs binaries in /opt/homebrew/bin/. The renderer.py I provided earlier automatically searches this path to find your ImageMagick (magick) installation.

    # Permissions: If MoviePy gives a "Security Policy" error, you may need to edit /opt/homebrew/etc/ImageMagick-7/policy.xml to allow "read/write" for PDF or text modules.