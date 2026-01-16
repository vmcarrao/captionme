import streamlit as st
import os
import shutil
from settings import (
    TEMP_DIR, OUTPUT_DIR, STYLES, STYLE_BOLD_REEL, STYLE_MINIMALIST, STYLE_DYNAMIC_POP,
    FONT_BOLD, FONT_MINIMAL, FONT_IMPACT, WHISPER_MODEL_SIZE
)
from drive_service import DriveService
from transcriber import Transcriber
from renderer import VideoRenderer

# --- App Config ---
st.set_page_config(page_title="CaptionME", page_icon="🎬", layout="wide")

@st.cache_resource
def get_transcriber():
    return Transcriber(model_size=WHISPER_MODEL_SIZE)

# --- Cleanup Function ---
def cleanup_temp_files():
    """Removes all files in TEMP_DIR and OUTPUT_DIR to save space."""
    try:
        shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR, exist_ok=True)
        # We might want to keep output for a bit, but user requested cleanup to save space.
        # Let's clean temp mainly.
        st.success(f"Cleaned up {TEMP_DIR}")
    except Exception as e:
        st.error(f"Error cleaning up: {e}")

# --- Main App ---
def main():
    # --- Custom CSS (Brutalist Theme) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Anton&family=JetBrains+Mono:wght@400;700&display=swap');

        /* Global RESET & Background */
        .stApp {
            background-color: #1a1a1a;
            color: #ffffff;
            font-family: 'JetBrains Mono', monospace;
        }

        /* HEADER styling */
        .brutalist-header {
            font-family: 'Anton', sans-serif;
            font-size: 8rem;
            text-transform: uppercase;
            color: #FFD700; /* Bold Yellow */
            line-height: 0.9;
            margin-bottom: 0px;
            letter-spacing: -2px;
        }
        .brutalist-sub {
            font-family: 'JetBrains Mono', monospace;
            color: #ffffff;
            font-size: 1.2rem;
            border-top: 2px solid #FFD700;
            border-bottom: 2px solid #FFD700;
            padding: 10px 0;
            margin-top: 10px;
            margin-bottom: 40px;
            display: flex;
            justify-content: space-between;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #000000;
            border-right: 2px solid #333;
        }
        [data-testid="stSidebar"] * {
            color: #ffffff !important;
            font-family: 'JetBrains Mono', monospace;
        }

        /* BUTTONS: Yellow PILLS/BLOCKS */
        div.stButton > button {
            background-color: #FFD700;
            color: #000000;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 700;
            text-transform: uppercase;
            border: 2px solid #FFD700;
            border-radius: 0px; /* Brutalist block */
            padding: 0.5rem 1rem;
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            background-color: #000000;
            color: #FFD700;
            border: 2px solid #FFD700;
        }

        /* Video Widget Sizing */
        [data-testid="stVideo"] {
            width: 300px !important; /* Slightly larger */
            height: auto !important;
            border: 2px solid #333;
            box-shadow: 10px 10px 0px #000; /* Drop shadow */
        }
        
        /* Headings */
        h1, h2, h3 {
            font-family: 'Anton', sans-serif !important;
            text-transform: uppercase;
            color: #ffffff !important;
        }
        
        /* Custom Dividers */
        hr {
            border-color: #333 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # --- Brutalist Header ---
    st.markdown("""
        <div style="text-align: center;">
            <div class="brutalist-header">CaptionME</div>
            <div class="brutalist-sub">
                <span>GEMINI 3 PRO</span>
                <span>•</span>
                <span>WHISPER AI</span>
                <span>•</span>
                <span>VERTICAL VIDEO</span>
                <span>•</span>
                <span>MISSION CONTROL</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # st.title("🎬 MacCaption Pro (M2 Optimized)") # Removed default title
    # st.markdown("### Transcribe & Caption Vertical Videos from Drive") # Removed default subheader

    # --- Sidebar ---
    with st.sidebar:
        st.header("Settings")
        st.write("Device: Apple Silicon (M1/M2)")
        if st.button("🧹 Purge Temp Files"):
            cleanup_temp_files()
            # Reset state to prevent trying to load deleted files
            st.session_state.selected_file = None
            st.session_state.local_video_path = None
            st.session_state.subtitles = []
            st.session_state.transcribed = False
            st.session_state.batch_index = 0
            st.rerun()
        st.divider()
        st.subheader("Timestamp Sync")
        sync_offset = st.number_input("Global Offset (ms)", value=0, step=100, help="Positive = Later, Negative = Earlier")
        if st.button("Apply Offset"):
            if st.session_state.subtitles:
                offset_seconds = sync_offset / 1000.0
                for sub in st.session_state.subtitles:
                    sub['start'] += offset_seconds
                    sub['end'] += offset_seconds
                    # Adjust words if present (for Dynamic Pop)
                    if 'words' in sub and sub['words']:
                         for w in sub['words']:
                             w['start'] += offset_seconds
                             w['end'] += offset_seconds
                st.success(f"Applied {sync_offset}ms offset!")
                st.rerun() # Refresh editor
            else:
                st.warning("No subtitles to sync.")
        
        st.divider()
        st.markdown("**Instructions:**")
        st.markdown("1. Select Video from Drive")
        st.markdown("2. Transcribe")
        st.markdown("3. Edit Subtitles")
        st.markdown("4. Render & Download")

    # --- State Management ---
    if "selected_file" not in st.session_state:
        st.session_state.selected_file = None
    if "local_video_path" not in st.session_state:
        st.session_state.local_video_path = None
    if "subtitles" not in st.session_state:
        st.session_state.subtitles = []
    if "transcribed" not in st.session_state:
        st.session_state.transcribed = False
    if "selected_batch" not in st.session_state:
        st.session_state.selected_batch = []
    if "batch_index" not in st.session_state:
        st.session_state.batch_index = 0
    
    if "processing_started" not in st.session_state:
        st.session_state.processing_started = False
    
    # --- Drive Integration ---
    st.subheader("1. 📂 Content Source")
    
    drive = DriveService()
    if drive.service:
        files = drive.list_files()
        file_options = {f"{f['name']}": f for f in files}
        
        # Ensure selected items are valid options (prevents errors on file deletion)
        valid_options = list(file_options.keys())
        st.session_state.selected_batch = [f for f in st.session_state.selected_batch if f in valid_options]
        
        # Checkbox List UI
        st.write("SELECT FLIGHT DATA RECORDERS (VIDEOS):")
        
        # Container for the list
        with st.container():
            # "Select All" / "Deselect All" Buttons
            col_actions, _ = st.columns([0.4, 0.6])
            with col_actions:
                 if st.button("Toggle All Selection"):
                     # Determine if we should select all or deselect all based on current state
                     if len(st.session_state.selected_batch) == len(valid_options):
                         st.session_state.selected_batch = []
                     else:
                         st.session_state.selected_batch = valid_options
                     st.rerun()

            st.divider()
            
            # The List
            new_selection = []
            for filename in valid_options:
                # check if currently selected
                is_checked = filename in st.session_state.selected_batch
                
                # Render checkbox
                # We use a unique key for each file
                checked = st.checkbox(
                    f"📄 {filename}", 
                    value=is_checked,
                    key=f"chk_{filename}"
                )
                
                if checked:
                    new_selection.append(filename)
            
            # Update the source of truth if changed
            # Note: In Streamlit, checkboxes update on interaction immediately. 
            # We just need to ensure selected_batch reflects the checkboxes next run.
            # However, since we re-calculate `new_selection` every run based on widget values, 
            # and widget values persist in session_state keys, we just assign it.
            st.session_state.selected_batch = new_selection

        if not st.session_state.selected_batch:
            st.info("Awaiting selection of at least one target...")
            st.session_state.processing_started = False # Reset if deselect all
            
        else:
            # Manual Trigger Button
            if not st.session_state.processing_started:
                 st.write("---")
                 if st.button("🚀 INITIATE TRANSCRIPTION SEQUENCE", type="primary"):
                     st.session_state.processing_started = True
                     st.rerun()

            if st.session_state.processing_started:
                # --- UNIFIED INTERACTIVE QUEUE ---
                # Determine Current File to Process
                is_batch = len(st.session_state.selected_batch) > 1
                if not is_batch:
                    # Single File Mode
                    current_filename = st.session_state.selected_batch[0]
                    current_index = 0
                    total_files = 1
                else:
                    # Batch Queue Mode
                    current_index = st.session_state.batch_index
                    total_files = len(st.session_state.selected_batch)
                    
                    # Check for completion
                    if current_index >= total_files:
                        st.success("🎉 All files in the batch have been processed!")
                        st.balloons()
                        if st.button("Start Over"):
                            st.session_state.batch_index = 0
                            st.rerun()
                        st.stop() # Stop rendering further UI
                    
                    current_filename = st.session_state.selected_batch[current_index]
                    st.markdown(f"### 🚀 Processing {current_index + 1}/{total_files}: {current_filename}")
                    st.progress((current_index) / total_files)

                # Get File Info
                file_info = file_options.get(current_filename)
                if not file_info:
                    st.error(f"File '{current_filename}' not found in current list.")
                    st.stop()

                # --- Auto-Load / Download Logic ---
                # Check if we need to load this new file
                is_new_file = (st.session_state.selected_file is None) or (st.session_state.selected_file.get('name') != current_filename)
                
                if is_new_file:
                     st.session_state.selected_file = file_info
                     with st.spinner(f"⬇️ Downloading {current_filename}..."):
                         local_path = drive.download_file(file_info['id'], file_info['name'], TEMP_DIR)
                         st.session_state.local_video_path = local_path
                         st.session_state.transcribed = False 
                         # For Batch Mode, auto-transcribe immediately after download to save a click
                         if is_batch:
                             st.session_state.auto_transcribe_trigger = True
                     st.rerun()

                # Display Video
                if st.session_state.local_video_path:
                    st.video(st.session_state.local_video_path)

                    # --- Transcription ---
                    st.subheader("2. 📝 Transcription")
                    
                    # Check for Auto-Transcribe Trigger
                    if st.session_state.get("auto_transcribe_trigger", False):
                         st.session_state.auto_transcribe_trigger = False # Reset
                         with st.spinner("🎙️ Auto-Transcribing for Batch Queue..."):
                            try:
                                transcriber = get_transcriber()
                                results = transcriber.transcribe_video(st.session_state.local_video_path)
                                st.session_state.subtitles = results
                                st.session_state.transcribed = True
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error during transcription: {e}")

                    if not st.session_state.transcribed:
                        if st.button("Start Transcription (faster-whisper)"):
                            status_text = st.empty()
                            status_text.text("⏳ Loading Whisper Model...")
                            try:
                                transcriber = get_transcriber()
                                status_text.text("🎙️ Transcribing audio...")
                                results = transcriber.transcribe_video(st.session_state.local_video_path)
                                st.session_state.subtitles = results
                                st.session_state.transcribed = True
                                status_text.success("Transcription complete!")
                                st.rerun()
                            except Exception as e:
                                status_text.error(f"Error during transcription: {e}")
                    
                    # --- Editing & Review ---
                    if st.session_state.transcribed:
                        st.success("✅ Transcribed")
                        st.subheader("3. ✏️ Review & Edit")
                        
                        edited_data = st.data_editor(
                            st.session_state.subtitles, 
                            num_rows="dynamic",
                            column_config={
                                "words": None
                            }
                        )
                        
                        # --- Rendering ---
                        st.subheader("4. 🎨 Style & Render")
                        selected_style = st.selectbox("Choose Caption Style", STYLES)
                        
                        # Style Customization
                        with st.expander("✨ Customize Style (Font, Size, Color)"):
                            col1, col2 = st.columns(2)
                            with col1:
                                available_fonts = [FONT_BOLD, FONT_MINIMAL, FONT_IMPACT, "Arial", "Helvetica", "Times New Roman"]
                                cust_font = st.selectbox("Font", available_fonts, index=0)
                                cust_fontsize = st.number_input("Font Size", value=70, step=5)
                                cust_stroke_width = st.number_input("Stroke Width", value=2, step=1)
                            with col2:
                                cust_color = st.color_picker("Text Color", "#FFFF00") # Yellow default
                                cust_stroke_color = st.color_picker("Stroke/Outline Color", "#000000")
                            
                            style_config = {
                                "font": cust_font,
                                "fontsize": cust_fontsize,
                                "color": cust_color,
                                "stroke_color": cust_stroke_color,
                                "stroke_width": cust_stroke_width
                            }
                            
                            if st.button("🖼️ Preview Style"):
                                 with st.spinner("Generating preview frame..."):
                                     renderer = VideoRenderer()
                                     preview_frame = renderer.generate_preview_frame(
                                         st.session_state.local_video_path,
                                         st.session_state.subtitles,
                                         selected_style,
                                         style_config
                                     )
                                     if preview_frame is not None:
                                         st.image(preview_frame, caption=f"Preview: {selected_style}", width=200)
                                     else:
                                         st.error("Could not generate preview.")

                        output_filename = f"captioned_{st.session_state.selected_file['name']}"
                        output_path = os.path.join(OUTPUT_DIR, output_filename)
                        
                        # Actions
                        col_b1, col_b2 = st.columns([1, 1])
                        
                        with col_b1:
                            # Dynamic Button Label
                            btn_label = "🔥 Render & Next Video ➡️" if is_batch else "🔥 Burn Captions"
                            
                            if st.button(btn_label, type="primary"):
                                with st.spinner("Rendering video (MoviePy)..."):
                                    renderer = VideoRenderer()
                                    final_path = renderer.render_video(
                                        st.session_state.local_video_path,
                                        edited_data,
                                        selected_style,
                                        output_path,
                                        style_config=style_config
                                    )
                                st.success(f"Rendering complete! Saved to {output_path}")
                                
                                if is_batch:
                                    # Advance Queue
                                    st.session_state.batch_index += 1
                                    st.rerun()

                        with col_b2:
                            if is_batch:
                                 if st.button("Skip Video ⏭️"):
                                     st.session_state.batch_index += 1
                                     st.rerun()
                        
                        # Download Link (Always available for current file)
                        if os.path.exists(output_path):
                             with open(output_path, "rb") as f:
                                st.download_button(
                                    label="Download Current Video",
                                    data=f,
                                    file_name=output_filename,
                                    mime="video/mp4"
                                )
    else:
        st.error("⚠️ Google Drive Integration Failed")
        st.warning("""
        **Authentication Credentials Not Found**
        
        To run this app on Streamlit Cloud, you must configure secrets:
        1. Go to your App Dashboard > **Settings** > **Secrets**.
        2. Create a section `[google_drive]`.
        3. Add your `token`, `client_id`, `client_secret`, etc.
        
        *If running locally, ensure `credentials.json` is in the root directory.*
        """)

if __name__ == "__main__":
    main()
