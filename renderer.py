import os
import shutil
import subprocess
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, ColorClip
from settings import (
    STYLE_BOLD_REEL, STYLE_MINIMALIST, STYLE_DYNAMIC_POP,
    FONT_BOLD, FONT_MINIMAL, FONT_IMPACT,
    VIDEO_WIDTH_VERTICAL, VIDEO_HEIGHT_VERTICAL
)

class VideoRenderer:
    def __init__(self):
        pass

    def _create_pil_text_image(self, text, font_path, fontsize, color, stroke_color=None, stroke_width=0, size=None):
        """
        Creates a numpy array image of text using PIL.
        Returns: numpy array (height, width, 4) suitable for ImageClip.
        """
        if not isinstance(text, str):
            text = str(text)
        
        # 1. Load Font
        fontsize = int(fontsize) # Ensure int
        stroke_width = int(stroke_width)
        
        print(f"DEBUG: Loading font '{font_path}' size={fontsize}")
        
        if not os.path.exists(font_path):
            print(f"WARNING: Font file not found at {font_path}. Using default.")
        
        try:
            font = ImageFont.truetype(font_path, fontsize)
        except Exception as e:
            print(f"PIL Error loading font {font_path}: {e}")
            # Fallback to default load if specific path fails
            try:
                font = ImageFont.load_default()
                print("Using default PIL font (fallback).")
                # Attempt to set size for default font if possible (Pillow 10+)
                try:
                    font = ImageFont.load_default(size=fontsize)
                except:
                    pass
            except:
                raise Exception("Could not load any font.")

        # 3. Create Image (with ample padding for strokes/glows)
        # Using anchor='mm' (middle-middle) to center text reliably
        
        # Measure with stroke included (rough estimate, as bbox doesn't always strictly include stroke)
        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        # Get standard bbox
        bbox = dummy_draw.textbbox((0, 0), text, font=font, anchor='mm', stroke_width=stroke_width)
        
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        W = int(text_w + stroke_width * 2 + 20)
        H = int(text_h + stroke_width * 2 + 20)
        
        img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw centered
        draw.text((W/2, H/2), text, font=font, fill=color, anchor='mm', stroke_width=stroke_width, stroke_fill=stroke_color)
        
        return np.array(img)

    def render_video(self, video_path: str, subtitles: List[Dict[str, Any]], style: str, output_path: str, style_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Renders the video with burned-in subtitles.
        """
        video = VideoFileClip(video_path)
        
        # Generator for creating clips
        subtitle_clips = []
        
        if style_config and style_config.get("karaoke"):
            subtitle_clips = self._create_karaoke_clips(subtitles, video.size, style_config, base_style=style)
        elif style == STYLE_BOLD_REEL:
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
        font_path = FONT_BOLD
        fontsize = 70
        color = 'yellow'
        stroke_color = 'black'
        stroke_width = 4 # slightly thicker for PIL
        
        if config:
            font_path = config.get('font', font_path)
            fontsize = config.get('fontsize', fontsize)
            color = config.get('color', color)
            stroke_color = config.get('stroke_color', stroke_color)
            stroke_width = config.get('stroke_width', stroke_width)

        for sub in subtitles:
            text_content = str(sub.get('text', '') or "")
            try:
                img_array = self._create_pil_text_image(
                    text_content, font_path, fontsize, color, stroke_color, stroke_width
                )
                
                txt_clip = (ImageClip(img_array)
                            .set_duration(sub['end'] - sub['start'])
                            .set_start(sub['start'])
                            .set_position(('center', 0.7*h)))
                            
                clips.append(txt_clip)
            except Exception as e:
                print(f"PIL Text Error: {e}")
                continue
        return clips

    def _create_minimalist_clips(self, subtitles: List[Dict[str, Any]], video_size: Tuple[int, int], config: Optional[Dict[str, Any]] = None) -> List[Any]:
        w, h = video_size
        clips = []
        
        # Defaults
        font_path = FONT_MINIMAL
        fontsize = 50
        color = 'white'
        
        if config:
            font_path = config.get('font', font_path)
            fontsize = config.get('fontsize', fontsize)
            color = config.get('color', color)
        
        for sub in subtitles:
            text_content = str(sub.get('text', '') or "")
            try:
                img_array = self._create_pil_text_image(
                    text_content, font_path, fontsize, color, stroke_width=0
                )
                
                txt_clip = (ImageClip(img_array)
                            .set_duration(sub['end'] - sub['start'])
                            .set_start(sub['start'])
                            .set_position('center')) # We'll adjust vertical below
                
                # Background box
                box_height = 150 # fixed height for aesthetic
                box_clip = (ColorClip(size=(w, box_height), color=(0,0,0))
                            .set_opacity(0.6)
                            .set_position(('center', 0.75*h - box_height/2))
                            .set_duration(sub['end'] - sub['start'])
                            .set_start(sub['start']))
                
                # Center text in box
                # Text clip height might vary, we center it relative to the box center
                # Box center Y is: 0.75*h
                txt_clip = txt_clip.set_position(('center', 0.75*h - img_array.shape[0]/2))
                
                clips.append(box_clip)
                clips.append(txt_clip)
            except Exception as e:
                print(f"PIL Text Error: {e}")
                continue
        return clips

    def _create_dynamic_pop_clips(self, subtitles: List[Dict[str, Any]], video_size: Tuple[int, int], config: Optional[Dict[str, Any]] = None) -> List[Any]:
        w, h = video_size
        clips = []
        
        # Defaults
        font_path = FONT_IMPACT
        fontsize = 100
        color = 'white'
        stroke_color = 'black'
        stroke_width = 5
        
        if config:
            font_path = config.get('font', font_path)
            fontsize = config.get('fontsize', fontsize)
            color = config.get('color', color)
            stroke_color = config.get('stroke_color', stroke_color)
            stroke_width = config.get('stroke_width', stroke_width)

        for sub in subtitles:
            words = sub.get('words', [])
            if not words:
                # Fallback to full text
                text_content = str(sub.get('text', '') or "")
                try:
                    img_array = self._create_pil_text_image(
                        text_content, font_path, int(fontsize*0.8), color, stroke_color, stroke_width
                    )
                    txt_clip = (ImageClip(img_array)
                                .set_duration(sub['end'] - sub['start'])
                                .set_start(sub['start'])
                                .set_position('center'))
                    clips.append(txt_clip)
                except:
                     pass
                continue

            for word_info in words:
                word_text = word_info['word']
                start = word_info['start']
                end = word_info['end']
                
                try:
                    img_array = self._create_pil_text_image(
                        word_text, font_path, fontsize, color, stroke_color, stroke_width
                    )
                    
                    # Highlight/Pop effect? (Maybe scale?)
                    # For now just render it center
                    txt_clip = (ImageClip(img_array)
                                .set_duration(end - start)
                                .set_start(start)
                                .set_position('center'))
                    
                    clips.append(txt_clip)
                except Exception as e:
                    print(f"PIL Word Error: {e}")
                    continue
                
        return clips

    def _create_karaoke_clips(self, subtitles: List[Dict[str, Any]], video_size: Tuple[int, int], config: Optional[Dict[str, Any]] = None, base_style: str = STYLE_BOLD_REEL) -> List[Any]:
        w, h = video_size
        clips = []

        # Defaults based on Base Style
        font_path = FONT_BOLD
        fontsize = 70
        stroke_width = 4
        active_color = 'yellow'
        inactive_color = 'white'
        stroke_color = 'black' # Default stroke
        
        # Style Specific Defaults
        if base_style == STYLE_MINIMALIST:
            font_path = FONT_MINIMAL
            fontsize = 50
            stroke_width = 0
            active_color = 'white' # Though user likely overrides
        elif base_style == STYLE_DYNAMIC_POP:
            font_path = FONT_IMPACT
            fontsize = 100
            stroke_width = 5
        
        # Override with Config
        if config:
            font_path = config.get('font', font_path)
            fontsize = config.get('fontsize', fontsize)
            active_color = config.get('color', active_color) 
            inactive_color = config.get('inactive_color', inactive_color)
            stroke_color = config.get('stroke_color', stroke_color)
            stroke_width = config.get('stroke_width', stroke_width)

        for sub in subtitles:
            words = sub.get('words', [])
            
            # If no words available, fallback to simple static text
            if not words:
                 text_content = str(sub.get('text', '') or "")
                 try:
                     img_array = self._create_pil_text_image(text_content, font_path, fontsize, active_color, stroke_color, stroke_width)
                     txt_clip = (ImageClip(img_array)
                                 .set_duration(sub['end'] - sub['start'])
                                 .set_start(sub['start'])
                                 .set_position(('center', 0.7*h))) # Default Pos
                     
                     if base_style == STYLE_MINIMALIST:
                         # Center and add box
                         txt_clip = txt_clip.set_position('center')
                         box_height = 150
                         box_clip = (ColorClip(size=(w, box_height), color=(0,0,0))
                                     .set_opacity(0.6)
                                     .set_position(('center', 0.75*h - box_height/2))
                                     .set_duration(sub['end'] - sub['start'])
                                     .set_start(sub['start']))
                         txt_clip = txt_clip.set_position(('center', 0.75*h - img_array.shape[0]/2))
                         clips.append(box_clip)

                     clips.append(txt_clip)
                 except:
                     pass
                 continue
            
            # Sentence level logic
            # We want to show the FULL sentence, but highlight words as they pass.
            # This means for a sentence with 5 words, we generate 5 clips (or N clips based on time).
            
            # 1. We need one clip per word duration
            for i, word_info in enumerate(words):
                start = word_info['start']
                end = word_info['end']

                try:
                    img_array = self._create_karaoke_pil_image(
                        words, i, font_path, fontsize, 
                        active_color, inactive_color, stroke_color, stroke_width
                    )
                    
                    pos = ('center', 0.7*h)
                    
                    if base_style == STYLE_MINIMALIST:
                        # Add box (once per word? or just rely on composition order?)
                        # We are adding clips sequentially. If we add a box clip for every word clip, it works.
                        box_height = 150
                        box_clip = (ColorClip(size=(w, box_height), color=(0,0,0))
                                    .set_opacity(0.6)
                                    .set_position(('center', 0.75*h - box_height/2))
                                    .set_duration(end - start)
                                    .set_start(start))
                        clips.append(box_clip)
                        
                        # Adjust text pos to center of box
                        pos = ('center', 0.75*h - img_array.shape[0]/2)

                    txt_clip = (ImageClip(img_array)
                                .set_duration(end - start)
                                .set_start(start)
                                .set_position(pos))
                    
                    clips.append(txt_clip)
                    
                    # Gap handling between this word and next?
                    if i < len(words) - 1:
                        next_start = words[i+1]['start']
                        if next_start > end:
                            gap_dur = next_start - end
                            # Avoid tiny clips
                            if gap_dur > 0.1:
                                gap_img = self._create_karaoke_pil_image(
                                    words, -1, font_path, fontsize,
                                    active_color, inactive_color, stroke_color, stroke_width
                                )
                                
                                gap_pos = ('center', 0.7*h)
                                if base_style == STYLE_MINIMALIST:
                                     # Gap Box
                                     box_clip_gap = (ColorClip(size=(w, box_height), color=(0,0,0))
                                            .set_opacity(0.6)
                                            .set_position(('center', 0.75*h - box_height/2))
                                            .set_duration(gap_dur)
                                            .set_start(end))
                                     clips.append(box_clip_gap)
                                     gap_pos = ('center', 0.75*h - gap_img.shape[0]/2)

                                gap_clip = (ImageClip(gap_img)
                                            .set_duration(gap_dur)
                                            .set_start(end)
                                            .set_position(gap_pos))
                                clips.append(gap_clip)
                except Exception as e:
                    print(f"Karaoke Render Error: {e}")
        
        return clips

    def _create_karaoke_pil_image(self, words_data, active_idx, font_path, fontsize, active_color, inactive_color, stroke_color, stroke_width):
        """Draws the entire sentence, but highlights words_data[active_idx]."""
        fontsize = int(fontsize)
        
        try:
            font = ImageFont.truetype(font_path, fontsize)
        except:
             font = ImageFont.load_default()
        
        # 1. Calculate dimensions
        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        
        total_width = 0
        max_height = 0
        spac_width = dummy_draw.textlength(" ", font=font)
        
        word_metrics = [] # (text, width, height)
        
        for w in words_data:
            txt = w['word']
            # bbox: left, top, right, bottom
            bbox = dummy_draw.textbbox((0, 0), txt, font=font, stroke_width=stroke_width)
            w_width = bbox[2] - bbox[0]
            w_height = bbox[3] - bbox[1]
            
            word_metrics.append({
                "text": txt,
                "width": w_width, 
                "height": w_height
            })
            
            total_width += w_width + spac_width
            max_height = max(max_height, w_height)
            
        total_width -= spac_width # Remove last space
        
        # Add padding
        W = int(total_width + 40)
        H = int(max_height + stroke_width*2 + 40)
        
        img = Image.new('RGBA', (W, H), (0,0,0,0))
        draw = ImageDraw.Draw(img)
        
        # 2. Draw words
        current_x = 20 # Padding left
        y_pos = H / 2
        
        for i, wm in enumerate(word_metrics):
            is_active = (i == active_idx)
            fill_c = active_color if is_active else inactive_color
            
            # Using anchor='lm' (left-middle) for sequence
            draw.text(
                (current_x, y_pos), 
                wm['text'], 
                font=font, 
                fill=fill_c, 
                anchor='lm', 
                stroke_width=stroke_width, 
                stroke_fill=stroke_color
            )
            
            current_x += wm['width'] + spac_width
            
        return np.array(img)

    def generate_preview_frame(self, video_path: str, subtitles: List[Dict[str, Any]], style: str, style_config: Optional[Dict[str, Any]] = None, time: Optional[float] = None) -> Any:
        """
        Generates a single frame preview.
        """
        video = VideoFileClip(video_path)
        
        if time is None:
            if subtitles:
                time = (subtitles[0]['start'] + subtitles[0]['end']) / 2
            else:
                time = video.duration / 2
        
        # Find active sub or dummy
        active_sub = None
        for sub in subtitles:
            if sub['start'] <= time <= sub['end']:
                active_sub = sub
                break
        
        if not active_sub:
             # Dummy
             active_sub = {'start': time-0.1, 'end': time+0.1, 'text': "Preview Caption", 'words': [{'word': "Preview", 'start': time-0.1, 'end': time}]}

        preview_subs = [active_sub]
        
        subtitle_clips = []
        subtitle_clips = []
        
        if style_config and style_config.get("karaoke"):
             subtitle_clips = self._create_karaoke_clips(preview_subs, video.size, style_config, base_style=style)
        elif style == STYLE_BOLD_REEL:
            subtitle_clips = self._create_bold_reel_clips(preview_subs, video.size, style_config)
        elif style == STYLE_DYNAMIC_POP:
            subtitle_clips = self._create_dynamic_pop_clips(preview_subs, video.size, style_config)
        elif style == STYLE_MINIMALIST: # Added back since it was removed in previous logic
            subtitle_clips = self._create_minimalist_clips(preview_subs, video.size, style_config)

            
        try:
             valid_clips = [c for c in subtitle_clips if c.start <= time <= c.end]
             final_comp = CompositeVideoClip([video] + valid_clips)
             return final_comp.get_frame(time)

        except Exception as e:
            print(f"Error generating preview: {e}")
            return None
