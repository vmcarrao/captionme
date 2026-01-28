import streamlit as st
import os
import shutil
from utils import download_google_fonts, fetch_google_font
from settings import (
    TEMP_DIR, OUTPUT_DIR, FONTS_DIR, STYLES, STYLE_BOLD_REEL, STYLE_MINIMALIST, STYLE_DYNAMIC_POP,
    FONT_BOLD, FONT_MINIMAL, FONT_IMPACT, WHISPER_MODEL_SIZE
)
from transcriber import Transcriber
from renderer import VideoRenderer
from presets_manager import PresetsManager

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
    # --- Runtime Setup ---
    # Ensure fonts are available (Download from Google if missing)
    download_google_fonts()

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
        </div>
    """, unsafe_allow_html=True)

    # st.title("🎬 MacCaption Pro (M2 Optimized)") # Removed default title
    # st.markdown("### Transcribe & Caption Vertical Videos from Drive") # Removed default subheader

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ Configuration")
        

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
        st.markdown("1. Upload Video (Drag & Drop)")
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
    if "saved_local_path" not in st.session_state:
        st.session_state.saved_local_path = ""
    
    if "processing_started" not in st.session_state:
        st.session_state.processing_started = False
    
    # --- Content Source (Drag & Drop) ---
    st.subheader("1. 📂 Content Source")
    
    uploaded_files = st.file_uploader(
        "Drop Flight Data Recorders (Videos) Here", 
        type=["mp4", "mov", "avi", "mkv"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        # Map filenames to file objects for easy access
        file_map = {f.name: f for f in uploaded_files}
        valid_options = list(file_map.keys())
        
        # Batch Selection Logic
        # By default, select all uploaded files for processing
        if "selected_batch" not in st.session_state or not st.session_state.selected_batch:
             st.session_state.selected_batch = valid_options
        else:
             # Filter out files that might have been removed
             st.session_state.selected_batch = [f for f in st.session_state.selected_batch if f in valid_options]
             # If completely empty after filter (e.g. user cleared uploader), reset
             if not st.session_state.selected_batch and valid_options:
                 st.session_state.selected_batch = valid_options

        # Display Selected Queue
        st.write(f"**Queue:** {len(st.session_state.selected_batch)} videos ready.")
        
        # Manual Trigger Button
        if not st.session_state.processing_started:
             st.write("---")
             if st.button("🚀 INITIATE TRANSCRIPTION SEQUENCE", type="primary"):
                 st.session_state.processing_started = True
                 st.rerun()

        if st.session_state.processing_started:
            current_index = st.session_state.batch_index
            total_files = len(st.session_state.selected_batch)
            
            # Check for completion
            if current_index >= total_files:
                st.success("🎉 All files in the batch have been processed!")
                st.balloons()
                
                # --- BATCH COMPLETION UI ---
                st.divider()
                st.subheader("📦 Batch Output Mission Debrief")
                
                col_zip, col_local = st.columns(2)
                
                # OPTION A: ZIP ARCHIVE (Cloud Friendly)
                with col_zip:
                    st.markdown("### ☁️ Download All")
                    st.info("Best for Cloud usage.")
                    
                    zip_base_name = os.path.join(TEMP_DIR, "captioned_videos")
                    # Create zip (overwrite if exists)
                    shutil.make_archive(zip_base_name, 'zip', OUTPUT_DIR)
                    zip_file_path = zip_base_name + ".zip"
                    
                    with open(zip_file_path, "rb") as f:
                        st.download_button(
                            label="📦 Download ZIP Archive",
                            data=f,
                            file_name="captioned_videos.zip",
                            mime="application/zip",
                            type="primary",
                            use_container_width=True
                        )

                # OPTION B: LOCAL SAVE (Local Friendly)
                with col_local:
                    st.markdown("### 💾 Local Save")
                    st.info("Move files to a local folder.")
                    
                    default_path = st.session_state.saved_local_path
                    local_dest = st.text_input("Destination Folder Path", value=default_path, placeholder="/Users/me/Movies/Captions")
                    remember = st.checkbox("Remember path for this session", value=True)
                    
                    if st.button("📂 Move Files to Folder", use_container_width=True):
                        if local_dest and os.path.exists(local_dest):
                            try:
                                files = os.listdir(OUTPUT_DIR)
                                count = 0
                                for f in files:
                                    if f.endswith(".mp4"):
                                        src = os.path.join(OUTPUT_DIR, f)
                                        dst = os.path.join(local_dest, f)
                                        shutil.copy2(src, dst) # Copy preserves metadata
                                        count += 1
                                
                                st.success(f"Successfully moved {count} videos to `{local_dest}`")
                                
                                if remember:
                                    st.session_state.saved_local_path = local_dest
                            except Exception as e:
                                st.error(f"Error moving files: {e}")
                        else:
                            st.error("❌ Invalid path or directory does not exist.")

                st.divider()
                if st.button("🔄 Start Over / Process New Batch"):
                    st.session_state.batch_index = 0
                    st.session_state.processing_started = False
                    # Keep selected_batch or clear it? 
                    # Usually better to keep selection so user can modify it.
                    st.rerun()
                st.stop() # Stop rendering further UI
            
            current_filename = st.session_state.selected_batch[current_index]
            is_batch = total_files > 1
            is_last_video = (current_index == total_files - 1)
            
            # Progress UI
            if is_batch:
                st.markdown(f"### 🚀 Processing {current_index + 1}/{total_files}: {current_filename}")
                st.progress((current_index) / total_files)
            else:
                 st.markdown(f"### 🚀 Processing: {current_filename}")

            # Get StreamlitUploadedFile
            uploaded_file = file_map.get(current_filename)
            if not uploaded_file:
                st.error(f"File '{current_filename}' missing from upload state.")
                st.stop()

            # --- Auto-Load / Download Logic ---
            # We need to save the BytesIO to a physical temp file for ffmpeg/processing
            expected_temp_path = os.path.join(TEMP_DIR, current_filename)
            
            if st.session_state.local_video_path != expected_temp_path:
                 with st.spinner(f"⬇️ Preparing {current_filename}..."):
                     with open(expected_temp_path, "wb") as f:
                         f.write(uploaded_file.getbuffer())
                     
                     st.session_state.local_video_path = expected_temp_path
                     st.session_state.selected_file = {'name': current_filename}
                     st.session_state.transcribed = False 
                     
                     # For Batch Mode, auto-transcribe
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
                    # Style Customization
                    with st.expander("✨ Customize Style (Font, Size, Color)"):
                        presets_mgr = PresetsManager()


                        # Layout: 3 Columns (Font Settings | Color Settings | Live Preview)
                        col_font, col_color, col_preview = st.columns([1.5, 1, 1.5]) # Adjusted ratios for better fit
                        
                        # --- COLUMN 1: FONT SETTINGS ---
                        with col_font:
                             available_fonts = [FONT_BOLD, FONT_MINIMAL, FONT_IMPACT]
                             
                             # Font Source
                             font_mode = st.radio(
                                 "Font Source", 
                                 ["Presets", "Custom Google Font"], 
                                 horizontal=True,
                                 key="font_source_mode"
                             )
                             
                             final_font_path = FONT_BOLD # Default
                             
                             if font_mode == "Presets":
                                 font_map = {
                                     "Roboto Bold": FONT_BOLD,
                                     "Roboto Regular": FONT_MINIMAL,
                                     "Anton Impact": FONT_IMPACT
                                 }
                                 current_font_selection = st.selectbox(
                                     "Choose Preset", 
                                     list(font_map.keys()),
                                     key="preset_font_choice"
                                 )
                                 final_font_path = font_map[current_font_selection]
                                 
                             else:
                                 google_font_name = st.text_input(
                                     "Enter Google Font Name", 
                                     value="Lobster",
                                     key="google_font_name_input"
                                 )
                                 current_font_selection = google_font_name 

                                 if st.button("Fetch Font"):
                                     with st.spinner(f"Fetching {google_font_name}..."):
                                         fetched_path = fetch_google_font(google_font_name)
                                         if fetched_path:
                                             st.success("Font downloaded!")
                                             final_font_path = fetched_path
                                             st.session_state.custom_font_path = fetched_path 
                                         else:
                                             st.error("Not found.")
                                 
                                 if "custom_font_path" in st.session_state:
                                     final_font_path = st.session_state.custom_font_path
                                     st.caption(f"Using: {os.path.basename(final_font_path)}")

                             cust_fontsize = st.number_input("Font Size", value=70, step=5, key="cust_fontsize")
                             cust_stroke_width = st.number_input("Stroke Width", value=2, step=1, key="cust_stroke_width")
                             
                             col_spacing_1, col_spacing_2 = st.columns(2)
                             with col_spacing_1:
                                 cust_letter_spacing = st.number_input("Letter Spacing", value=0, step=1, key="cust_letter_spacing")
                             with col_spacing_2:
                                 cust_line_spacing = st.number_input("Line Spacing", value=0, step=5, key="cust_line_spacing")
                             
                             st.write("")
                             chk_karaoke = st.checkbox("🎵 Karaoke Effect", key="chk_karaoke", help="Highlight words as they are spoken.")

                        # --- COLUMN 2: COLOR SETTINGS ---
                        with col_color:
                             if chk_karaoke:
                                 st.markdown("**Karaoke Colors**")
                                 cust_color = st.color_picker("Active Word", "#FFFF00", key="cust_color")
                                 cust_inactive_color = st.color_picker("Inactive Word", "#FFFFFF", key="cust_inactive_color")
                             else:
                                 st.markdown("**Text Colors**")
                                 cust_color = st.color_picker("Text Color", "#FFFF00", key="cust_color")
                                 cust_inactive_color = "#FFFFFF" 
                                 
                             cust_stroke_color = st.color_picker("Stroke Color", "#000000", key="cust_stroke_color")
                        
                        # Prepare Config for Preview
                        style_config = {
                            "font": final_font_path,
                            "fontsize": cust_fontsize,
                            "color": cust_color,
                            "inactive_color": cust_inactive_color,
                            "stroke_color": cust_stroke_color,
                            "stroke_width": cust_stroke_width,
                            "karaoke": chk_karaoke,
                            "letter_spacing": cust_letter_spacing,
                            "line_spacing": cust_line_spacing
                        }

                        # --- COLUMN 3: LIVE PREVIEW ---
                        with col_preview:
                             st.markdown("**Live Preview**")
                             if st.session_state.local_video_path and st.session_state.subtitles:
                                  # Container to keep height stable?
                                  preview_container = st.container()
                                  try:
                                      renderer = VideoRenderer()
                                      # We generate preview for the CURRENT config
                                      preview_frame = renderer.generate_preview_frame(
                                          st.session_state.local_video_path,
                                          st.session_state.subtitles,
                                          selected_style,
                                          style_config
                                      )
                                      if preview_frame is not None:
                                          preview_container.image(preview_frame, width=350)
                                      else:
                                          preview_container.error("Preview failed.")
                                  except Exception as e:
                                      preview_container.error(f"Error: {e}")
                             else:
                                  st.info("Load video to see preview.")

                        st.markdown("---")

                        # --- PRESET MANAGER (Load & Save) ---
                        st.write("#### 💾 Presets Manager")
                        
                        # --- Callback for Loading Presets ---
                        def load_preset_callback():
                             selected_loader = st.session_state.get("preset_loader")
                             if selected_loader and selected_loader != "None":
                                 mgr = PresetsManager()
                                 data = mgr.get_preset(selected_loader)
                                 if data:
                                     # Update Session State directly
                                     st.session_state.font_source_mode = data.get("font_mode", "Presets")
                                     
                                     if data.get("font_mode") == "Presets":
                                         st.session_state.preset_font_choice = data.get("font_selection")
                                     else:
                                         st.session_state.google_font_name_input = data.get("font_selection")
                                         
                                     st.session_state.cust_fontsize = data.get("fontsize", 70)
                                     st.session_state.cust_stroke_width = data.get("stroke_width", 2)
                                     st.session_state.cust_color = data.get("color", "#FFFF00")
                                     st.session_state.cust_stroke_color = data.get("stroke_color", "#000000")
                                     st.session_state.chk_karaoke = data.get("karaoke", False)
                                     if "inactive_color" in data:
                                          st.session_state.cust_inactive_color = data.get("inactive_color")
                                     
                                     st.session_state.preset_loaded_msg = f"Loaded '{selected_loader}'"

                        # 1. LOADER
                        all_presets = presets_mgr.get_all_names()
                        preset_options = ["None"] + all_presets
                        
                        col_p1, col_p2 = st.columns([3, 1])
                        with col_p1:
                            selected_preset_load = st.selectbox("📂 Load Saved Preset", preset_options, key="preset_loader")
                        with col_p2:
                            st.write("") 
                            st.write("") 
                            st.button("Load Preset", on_click=load_preset_callback)
                        
                        if "preset_loaded_msg" in st.session_state:
                            st.success(st.session_state.preset_loaded_msg)
                            del st.session_state.preset_loaded_msg

                        # 2. SAVER
                        col_s1, col_s2 = st.columns([3, 1])
                        with col_s1:
                            new_preset_name = st.text_input("New Preset Name", placeholder="My Custom Style")
                        with col_s2:
                            st.write("")
                            st.write("") 
                            if st.button("Save Preset"):
                                if new_preset_name:
                                    config_to_save = {
                                        "font_mode": font_mode,
                                        "font_selection": current_font_selection,
                                        "fontsize": cust_fontsize,
                                        "stroke_width": cust_stroke_width,
                                        "color": cust_color,
                                        "inactive_color": cust_inactive_color,
                                        "stroke_color": cust_stroke_color,
                                        "karaoke": chk_karaoke
                                    }
                                    presets_mgr.save_preset(new_preset_name, config_to_save)
                                    st.success(f"Saved: {new_preset_name}")
                                    st.rerun()
                                else:
                                    st.warning("Enter a name.")

                    output_filename = f"captioned_{st.session_state.selected_file['name']}"
                    output_path = os.path.join(OUTPUT_DIR, output_filename)
                    is_rendered = os.path.exists(output_path)
                    
                    st.divider()
                    
                    # --- ACTION AREA ---
                    st.divider()
                    
                    # --- ACTION AREA ---
                    
                    # STEP 1: ALWAYS SHOW BURN BUTTON
                    if st.button("🔥 Burn Captions", type="primary", use_container_width=True):
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
                         # Force re-check of file existence by updating state or just rerun
                         st.rerun()

                    # STEP 2: POST-RENDER ACTIONS (If file exists)
                    if is_rendered:
                        st.success(f"✅ Render Complete: {output_filename}")
                        
                        col_actions_1, col_actions_2 = st.columns(2)
                        
                        # LEFT COL: Save/Download Current
                        with col_actions_1:
                            st.markdown("#### 💾 Save Current Video")
                            
                            # 1. Browser Download
                            with open(output_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download (Browser)",
                                    data=f,
                                    file_name=output_filename,
                                    mime="video/mp4"
                                )
                                
                            # 2. Local Folder Move
                            st.markdown("---")
                            default_path = st.session_state.saved_local_path
                            local_dest = st.text_input("Local Folder Path", value=default_path, placeholder="/Users/me/Movies")
                            remember = st.checkbox("Remember path", value=True, key="remember_current")
                            
                            if st.button("📂 Move to Folder"):
                                if local_dest and os.path.exists(local_dest):
                                    try:
                                        dst = os.path.join(local_dest, output_filename)
                                        shutil.copy2(output_path, dst)
                                        st.success(f"Saved to `{local_dest}`")
                                        if remember:
                                            st.session_state.saved_local_path = local_dest
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                                else:
                                    st.error("Invalid folder.")

                        # RIGHT COL: Navigation
                        with col_actions_2:
                            st.markdown("#### ⏩ Navigation")
                            
                            if is_batch:
                                # Determine if Last Video
                                # is_last_video defined above
                                
                                if not is_last_video:
                                    if st.button("Next Video ➡️", type="primary", use_container_width=True):
                                        st.session_state.batch_index += 1
                                        st.rerun()
                                else:
                                    st.info("This was the last video in the batch.")
                                    # Option to Go to Summary (which has Download All)
                                    if st.button("🏁 Finish & View Batch Results", type="primary", use_container_width=True):
                                        st.session_state.batch_index += 1
                                        st.rerun()
                            else:
                                st.info("Single file processed.")

                    # Skip Logic (Always available if not rendered or if user wants to skip despite render)
                    if is_batch and not is_last_video: # Only show skip if not last
                         st.markdown("---")
                         if st.button("Skip Video ⏭️"):
                             st.session_state.batch_index += 1
                             st.rerun()
    else:
        st.info("👋 Welcome to CaptionME. Drag & drop video files above to begin.")

if __name__ == "__main__":
    main()
