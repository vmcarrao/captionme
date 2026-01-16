import os
import shutil
import subprocess
from typing import List, Dict, Any, Optional, Tuple, Union
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
from settings import (
    STYLE_BOLD_REEL, STYLE_MINIMALIST, STYLE_DYNAMIC_POP,
    FONT_BOLD, FONT_MINIMAL, FONT_IMPACT,
    VIDEO_WIDTH_VERTICAL, VIDEO_HEIGHT_VERTICAL
)

# --- MacOS & Linux fix for ImageMagick ---
def get_imagemagick_binary():
    """Attempts to find the ImageMagick binary."""
    # Common paths on macOS/Homebrew and Linux
    possible_names = ["magick", "convert"]
    
    # Check PATH first
    for name in possible_names:
        path = shutil.which(name)
        if path:
            return path
            
    # Fallback to searching via subprocess if not in PATH (Linux/Mac specific locations)
    # Streamlit Cloud/Linux often has valid binary in /usr/bin/convert or /usr/bin/magick
    possible_paths = [
        "/usr/bin/convert", 
        "/usr/bin/magick", 
        "/usr/local/bin/convert", 
        "/usr/local/bin/magick"
    ]
    
    for p in possible_paths:
        if os.path.exists(p):
            return p

    try:
        # MacOS specific fallback
        cmd = ["/usr/bin/find", "/opt/homebrew", "-name", "magick", "-type", "f"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip().split('\n')[0]
    except Exception:
        pass

    return None

IMAGEMAGICK_BINARY = get_imagemagick_binary()
if IMAGEMAGICK_BINARY:
    os.environ["IMAGEMAGICK_BINARY"] = IMAGEMAGICK_BINARY
    from moviepy.config import change_settings
    change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})
    print(f"ImageMagick binary configured: {IMAGEMAGICK_BINARY}")
else:
    print("Warning: ImageMagick binary not found. MoviePy TextClips might fail.")
    # Attempt to print environment for debugging in logs
    print(f"PATH environment: {os.environ.get('PATH')}")


class VideoRenderer:
    def __init__(self):
        pass


    def render_video(self, video_path: str, subtitles: List[Dict[str, Any]], style: str, output_path: str, style_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Renders the video with burned-in subtitles based on the selected style.
        subtitles: list of dicts {'start': float, 'end': float, 'text': str, 'words': list}
        style_config: dict with keys 'font', 'fontsize', 'color', 'stroke_color', 'stroke_width' (optional)
        """
        video = VideoFileClip(video_path)
        
        # Generator for creating clips
        subtitle_clips = []
        
        if style == STYLE_BOLD_REEL:
            subtitle_clips = self._create_bold_reel_clips(subtitles, video.size, style_config)
        elif style == STYLE_MINIMALIST:
            subtitle_clips = self._create_minimalist_clips(subtitles, video.size, style_config)
        elif style == STYLE_DYNAMIC_POP:
            subtitle_clips = self._create_dynamic_pop_clips(subtitles, video.size, style_config)
        else:
             # Default fallback
             subtitle_clips = self._create_bold_reel_clips(subtitles, video.size, style_config)

        final_video = CompositeVideoClip([video] + subtitle_clips)
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")
        
        return output_path

    def _create_bold_reel_clips(self, subtitles: List[Dict[str, Any]], video_size: Tuple[int, int], config: Optional[Dict[str, Any]] = None) -> List[Any]:
        w, h = video_size
        clips = []
        
        # Defaults
        font = FONT_BOLD
        fontsize = 70
        color = 'yellow'
        stroke_color = 'black'
        stroke_width = 2
        
        if config:
            font = config.get('font', font)
            fontsize = config.get('fontsize', fontsize)
            color = config.get('color', color)
            stroke_color = config.get('stroke_color', stroke_color)
            stroke_width = config.get('stroke_width', stroke_width)

        for sub in subtitles:
            text_content = sub.get('text', '')
            if text_content is None:
                text_content = ""
            
            # Ensure it's a string
            text_content = str(text_content)

            txt_clip = (TextClip(text_content, fontsize=fontsize, font=font, color=color, stroke_color=stroke_color, stroke_width=stroke_width, method='caption', size=(w*0.8, None))
                        .set_position(('center', 0.7*h)) # Bottom-center
                        .set_start(sub['start'])
                        .set_end(sub['end']))
            clips.append(txt_clip)
        return clips

    def _create_minimalist_clips(self, subtitles: List[Dict[str, Any]], video_size: Tuple[int, int], config: Optional[Dict[str, Any]] = None) -> List[Any]:
        w, h = video_size
        clips = []
        
        # Defaults
        font = FONT_MINIMAL
        fontsize = 50
        color = 'white'
        
        if config:
            font = config.get('font', font)
            fontsize = config.get('fontsize', fontsize)
            color = config.get('color', color)
            # Minimalist usually doesn't have stroke, but we can respect it if passed explicitly
        
        for sub in subtitles:
            text_content = str(sub.get('text', '') or "")
            # Create text first to measure it (approximation) or fixed size
            txt_clip = (TextClip(text_content, fontsize=fontsize, font=font, color=color, method='caption', size=(w*0.8, None))
                        .set_position('center'))
            
            # Create a semi-transparent black box behind it
            # Note: TextClip size isn't always perfect for backgrounds without more complex logic, 
            # so we'll make a fixed height box near the bottom.
            
            box_height = 150 # approximate
            box_clip = (ColorClip(size=(w, box_height), color=(0,0,0))
                        .set_opacity(0.6)
                        .set_position(('center', 0.75*h - box_height/2))
                        .set_start(sub['start'])
                        .set_end(sub['end']))
            
            txt_clip = txt_clip.set_position(('center', 0.75*h - box_height/2 + (box_height - txt_clip.h)/2)).set_start(sub['start']).set_end(sub['end'])
            
            clips.append(box_clip)
            clips.append(txt_clip)
        return clips

    def _create_dynamic_pop_clips(self, subtitles: List[Dict[str, Any]], video_size: Tuple[int, int], config: Optional[Dict[str, Any]] = None) -> List[Any]:
        """
        Word-by-word display. Requires 'words' in subtitle data provided by faster-whisper.
        """
        w, h = video_size
        clips = []
        
        # Defaults
        font = FONT_IMPACT
        fontsize = 100
        color = 'white'
        stroke_color = 'black'
        stroke_width = 3
        
        if config:
             font = config.get('font', font)
             fontsize = config.get('fontsize', fontsize) # maybe scale this up for pop effect?
             color = config.get('color', color)
             stroke_color = config.get('stroke_color', stroke_color)
             stroke_width = config.get('stroke_width', stroke_width)

        
        for sub in subtitles:
            words = sub.get('words', [])
            if not words:
                text_content = str(sub.get('text', '') or "")
                # Fallback if no word-level timestamps
                txt_clip = (TextClip(text_content, fontsize=fontsize*0.8, font=font, color=color, stroke_color=stroke_color, stroke_width=stroke_width, method='caption', size=(w*0.9, None))
                        .set_position('center')
                        .set_start(sub['start'])
                        .set_end(sub['end']))
                clips.append(txt_clip)
                continue

            for word_info in words:
                # word_info is typically {start, end, word, probability}
                word_text = word_info['word']
                start = word_info['start']
                end = word_info['end']
                
                # Make it pop! Huge font, center screen
                txt_clip = (TextClip(word_text, fontsize=fontsize, font=font, color=color, stroke_color=stroke_color, stroke_width=stroke_width)
                            .set_position('center')
                            .set_start(start)
                            .set_end(end))
                clips.append(txt_clip)
                
        return clips

    def generate_preview_frame(self, video_path: str, subtitles: List[Dict[str, Any]], style: str, style_config: Optional[Dict[str, Any]] = None, time: Optional[float] = None) -> Any:
        """
        Generates a single frame preview at a specific time (or middle of first subtitle).
        """
        video = VideoFileClip(video_path)
        
        if time is None:
            # Pick a time from the first subtitle, or middle of video
            if subtitles:
                time = (subtitles[0]['start'] + subtitles[0]['end']) / 2
            else:
                time = video.duration / 2
        
        # Create a temporary mini-subtitle list for just this moment to reuse logic
        # Ideally we'd just create one clip, but reusing the existing methods ensures 1:1 match
        
        # We need to find the subtitle actively shown at 'time'
        active_sub = None
        for sub in subtitles:
            if sub['start'] <= time <= sub['end']:
                active_sub = sub
                break
        
        if not active_sub and subtitles:
             # Just force the first one for preview if nothing at exact time
             active_sub = subtitles[0]
             time = (active_sub['start'] + active_sub['end']) / 2
        
        if not active_sub:
             # No subtitles at all using dummy text
             active_sub = {'start': time-1, 'end': time+1, 'text': "Preview Caption Text", 'words': [{'word': "Preview", 'start': time-1, 'end': time}, {'word': "Caption", 'start': time, 'end': time+1}]}

        preview_subs = [active_sub]
        
        # Generate clips
        subtitle_clips = []
        if style == STYLE_BOLD_REEL:
            subtitle_clips = self._create_bold_reel_clips(preview_subs, video.size, style_config)
        elif style == STYLE_MINIMALIST:
            subtitle_clips = self._create_minimalist_clips(preview_subs, video.size, style_config)
        elif style == STYLE_DYNAMIC_POP:
            subtitle_clips = self._create_dynamic_pop_clips(preview_subs, video.size, style_config)
            
        # Composite just for that frame
        try:
             # Filter clips valid at this time
             valid_clips = [c for c in subtitle_clips if c.start <= time <= c.end]
             
             # Get video frame
             frame_img = video.get_frame(time)
             
             # Create a composite of the text clips on top of a transparent background of video size
             # Then overlay that on the frame? 
             # Easier: Create a CompositeVideoClip of [Video, Text] and get_frame
             # But VideoFileClip might be heavy. 
             # Let's try to just blit the text clip on the frame.
             
             # Actually, CompositeVideoClip.get_frame(t) is robust.
             final_comp = CompositeVideoClip([video] + valid_clips)
             return final_comp.get_frame(time)

        except Exception as e:
            print(f"Error generating preview: {e}")
            return None
