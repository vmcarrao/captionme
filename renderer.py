import os
import shutil
import subprocess
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageFont, ImageDraw
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, ColorClip, VideoClip
from settings import (
    STYLE_BOLD_REEL, STYLE_MINIMALIST, STYLE_DYNAMIC_POP,
    FONT_BOLD, FONT_MINIMAL, FONT_IMPACT,
    VIDEO_WIDTH_VERTICAL, VIDEO_HEIGHT_VERTICAL
)

class VideoRenderer:
    def __init__(self):
        pass

    def _wrap_text_pixel(self, text: str, font: ImageFont.FreeTypeFont, max_width: int, letter_spacing: int = 0) -> str:
        """Helper to wrap text based on pixel width."""
        words = text.split()
        if not words:
            return ""
            
        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        lines = []
        current_line = []
        
        def get_width(t):
            base_w = dummy_draw.textlength(t, font=font)
            if len(t) > 1:
                return base_w + (len(t) - 1) * letter_spacing
            return base_w

        for word in words:
            # Check width of (current_line + word)
            test_line = " ".join(current_line + [word])
            w = get_width(test_line)
            
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Word itself is too long, just add it
                    lines.append(word)
                    current_line = []
        
        if current_line:
            lines.append(" ".join(current_line))
            
        return "\n".join(lines)

    def _draw_text_with_spacing(self, draw, xy, text, font, fill, letter_spacing, anchor='ls', stroke_width=0, stroke_fill=None):
        """Helper to draw text with letter spacing using Baseline alignment."""
        x, y = xy
        
        # If no spacing, just draw
        if letter_spacing == 0:
            draw.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke_width, stroke_fill=stroke_fill)
            return
            
        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))

        # Prepare for manual drawing
        current_x = x
        current_y = y
        
        # Resolve 'mm' (Middle Middle) to 'ls' (Left Baseline) if needed
        # (Only simple mapping implemented for common use cases in this app)
        if anchor == 'mm':
            # Horizontal: Center
            base_w = dummy_draw.textlength(text, font=font)
            total_w = base_w + (len(text) - 1) * letter_spacing
            current_x = x - total_w / 2
            
            # Vertical: Middle to Baseline
            ascent, descent = font.getmetrics()
            # Middle of text block height (ascent+descent) is roughly (ascent-descent)/2 above baseline?
            # Height = ascent + descent. Bottom is y + height/2. Top is y - height/2.
            # Baseline is Top + ascent.
            # So Baseline = (y - height/2) + ascent = y - (ascent+descent)/2 + ascent
            # = y + (ascent - descent) / 2
            current_y = y + (ascent - descent) / 2
        
        elif anchor == 'la':
             # Left Ascender -> Left Baseline
             ascent, descent = font.getmetrics()
             current_y = y + ascent
        
        # Default/Expected: 'ls' (Left Baseline)
        # We iterate characters drawing at Baseline to keep them aligned.
        
        for char in text:
            draw.text((current_x, current_y), char, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill, anchor='ls')
            w = dummy_draw.textlength(char, font=font)
            current_x += w + letter_spacing

    def _create_pil_text_image(self, text, font_path, fontsize, color, stroke_color=None, stroke_width=0, size=None, letter_spacing=0, line_spacing=0):
        """
        Creates a numpy array image of text using PIL.
        Returns: numpy array (height, width, 4) suitable for ImageClip.
        """
        if not isinstance(text, str):
            text = str(text)
        
        # 1. Load Font
        fontsize = int(fontsize) # Ensure int
        stroke_width = int(stroke_width)
        
        if not os.path.exists(font_path):
            pass # Suppress warning spam or log once
        
        try:
            font = ImageFont.truetype(font_path, fontsize)
        except:
            font = ImageFont.load_default()
            try:
                font = ImageFont.load_default(size=fontsize)
            except:
                pass

        # 3. Create Image (with ample padding for strokes/glows)
        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        
        lines = text.split('\n')
        
        # Calculate Dimensions and Line Properties
        ascent, descent = font.getmetrics()
        line_height = ascent + descent
        total_h = len(lines) * line_height + (len(lines) - 1) * line_spacing
        
        max_w = 0
        line_widths = []
        for line in lines:
            base_w = dummy_draw.textlength(line, font=font)
            if len(line) > 1:
                w = base_w + (len(line) - 1) * letter_spacing
            else:
                w = base_w
            line_widths.append(w)
            max_w = max(max_w, w)
            
        W = int(max_w + stroke_width * 2 + 40)
        H = int(total_h + stroke_width * 2 + 40)
        
        img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Shadow Settings
        shadow_offset = (4, 4)
        shadow_color = (0, 0, 0, 160)
        
        # Draw Lines
        # Calculate visual top start
        # total_h is the height of the block
        # Middle of block is H/2. Top of block is H/2 - total_h/2.
        
        block_top_y = (H - total_h) / 2
        
        current_baseline_y = block_top_y + ascent # First line baseline
        
        for i, line in enumerate(lines):
            line_w = line_widths[i]
            # Center X
            center_x = W / 2
            
            # Draw Shadow
            self._draw_text_with_spacing(
                draw, 
                (center_x + shadow_offset[0], current_baseline_y + shadow_offset[1]), 
                line, font, shadow_color, letter_spacing, 
                anchor='mm', # Helper maps mm to baseline
                stroke_width=stroke_width, stroke_fill=shadow_color
            )
            
            # Main Text
            self._draw_text_with_spacing(
                draw, 
                (center_x, current_baseline_y), 
                line, font, color, letter_spacing, 
                anchor='mm', 
                stroke_width=stroke_width, stroke_fill=stroke_color
            )
            
            current_baseline_y += line_height + line_spacing
            
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
        letter_spacing = 0
        line_spacing = 0
        
        if config:
            font_path = config.get('font', font_path)
            fontsize = config.get('fontsize', fontsize)
            color = config.get('color', color)
            stroke_color = config.get('stroke_color', stroke_color)
            stroke_width = config.get('stroke_width', stroke_width)
            letter_spacing = config.get('letter_spacing', 0)
            line_spacing = config.get('line_spacing', 0)

        for sub in subtitles:
            text_content = str(sub.get('text', '') or "")
            try:
                # Load font for measuring
                try:
                    font = ImageFont.truetype(font_path, int(fontsize))
                except:
                    font = ImageFont.load_default()

                # Wrap text
                max_width = int(w * 0.9)
                wrapped_text = self._wrap_text_pixel(text_content, font, max_width, letter_spacing=letter_spacing)

                img_array = self._create_pil_text_image(
                    wrapped_text, font_path, fontsize, color, stroke_color, stroke_width, 
                    letter_spacing=letter_spacing, line_spacing=line_spacing
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
                # Load font for measuring
                try:
                    font = ImageFont.truetype(font_path, int(fontsize))
                except:
                    font = ImageFont.load_default()
                
                max_width = int(w * 0.9)
                wrapped_text = self._wrap_text_pixel(text_content, font, max_width)

                img_array = self._create_pil_text_image(
                    wrapped_text, font_path, fontsize, color, stroke_width=0
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
                    # Load font for measuring
                    try:
                        font = ImageFont.truetype(font_path, int(fontsize*0.8))
                    except:
                        font = ImageFont.load_default()

                    max_width = int(w * 0.9)
                    wrapped_text = self._wrap_text_pixel(text_content, font, max_width)

                    img_array = self._create_pil_text_image(
                        wrapped_text, font_path, int(fontsize*0.8), color, stroke_color, stroke_width
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
                     # Load font
                     try:
                         font = ImageFont.truetype(font_path, int(fontsize))
                     except:
                         font = ImageFont.load_default()
                     
                     max_width = int(w * 0.9)
                     wrapped_text = self._wrap_text_pixel(text_content, font, max_width)

                     img_array = self._create_pil_text_image(wrapped_text, font_path, fontsize, active_color, stroke_color, stroke_width)
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
            
            # EFFICIENT VIDEO CLIP GENERATION
            # Instead of creating N ImageClips (one per word), we create 1 VideoClip per sentence
            # using a make_frame function that renders text on demand.
            
            try:
                max_width = int(w * 0.9)
                sentence_clip = self._create_karaoke_sentence_clip(
                    sub, font_path, fontsize, active_color, inactive_color, stroke_color, stroke_width, max_width,
                    letter_spacing=config.get('letter_spacing', 0) if config else 0,
                    line_spacing=config.get('line_spacing', 0) if config else 0
                )
                
                # Positioning
                pos = ('center', 0.7*h)
                
                if base_style == STYLE_MINIMALIST:
                    # Add background box clip (static)
                    box_height = 150
                    box_clip = (ColorClip(size=(w, box_height), color=(0,0,0))
                                .set_opacity(0.6)
                                .set_position(('center', 0.75*h - box_height/2))
                                .set_duration(sentence_clip.duration)
                                .set_start(sentence_clip.start))
                    clips.append(box_clip)
                    
                    # Recenter text relative to box (approx using clip.size if available, or just same baseline)
                    if hasattr(sentence_clip, 'h'):
                        pos = ('center', 0.75*h - sentence_clip.h / 2)
                    else:
                         pos = ('center', 0.75*h - 50) # fallback

                sentence_clip = sentence_clip.set_position(pos)
                clips.append(sentence_clip)
                
            except Exception as e:
                print(f"Karaoke VideoClip Error: {e}")
                continue
                
        return clips

    def _create_karaoke_sentence_clip(self, sub, font_path, fontsize, active_color, inactive_color, stroke_color, stroke_width, max_width, letter_spacing=0, line_spacing=0):
        """
        Creates a single VideoClip for the whole sentence that highlights words over time.
        Uses cached font and pre-calculated layout to save memory.
        """
        words = sub.get('words', [])
        start_time = sub['start']
        end_time = sub['end']
        duration = end_time - start_time
        
        fontsize = int(fontsize)
        try:
            font = ImageFont.truetype(font_path, fontsize)
        except:
            font = ImageFont.load_default()
            
        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        
        # --- PRE-CALCULATE LAYOUT (Once per sentence) ---
        try:
            ascent, descent = font.getmetrics()
        except:
            ascent, descent = fontsize, fontsize * 0.2
        
        line_height = ascent + descent
        space_width = dummy_draw.textlength(" ", font=font) * 0.8 # Tighter spacing for karaoke
        
        processed_words = []
        for w_obj in words:
            txt = w_obj.get('text') or w_obj.get('word')
            if not txt:
                continue
            base_w = dummy_draw.textlength(txt, font=font)
            # Add spacing only between chars, so (len-1) * spacing
            char_spacing_total = (len(txt) - 1) * letter_spacing if len(txt) > 1 else 0
            w_width = base_w + char_spacing_total
            processed_words.append({"text": txt, "width": w_width, "obj": w_obj})
            
        lines = []
        current_line = []
        current_line_width = 0
        max_total_width = 0
        
        for i, pwm in enumerate(processed_words):
            word_w = pwm['width']
            space = space_width if current_line else 0
            new_width = current_line_width + space + word_w
            
            if max_width and new_width > max_width and current_line:
                lines.append({"words": current_line, "width": current_line_width})
                max_total_width = max(max_total_width, current_line_width)
                current_line = [i]
                current_line_width = word_w
            else:
                current_line.append(i)
                current_line_width = new_width
                
        if current_line:
            lines.append({"words": current_line, "width": current_line_width})
            max_total_width = max(max_total_width, current_line_width)
            
        vertical_spacing = line_spacing # User defined or 0
        total_content_height = len(lines) * line_height + (len(lines) - 1) * vertical_spacing
        
        padding_x = 40 + stroke_width * 2
        padding_y = 40 + stroke_width * 2
        W = int(max_total_width + padding_x)
        H = int(total_content_height + padding_y)
        
        # --- MAKE_FRAME FUNCTION ---
        # --- MAKE_FRAME FUNCTION ---
        # Cache to avoid double rendering (Color + Mask)
        # Simple specific cache for this clip instance
        last_render = {"t": -1, "img": None}
        
        def render_rgba(t):
            # Check cache (allow small float tolerance)
            if abs(t - last_render["t"]) < 0.0001 and last_render["img"] is not None:
                return last_render["img"]
                
            # t is time relative to clip start
            current_abs_time = start_time + t
            
            # Identify active word index
            active_idx = -1
            for i, w_obj in enumerate(words):
                if w_obj['start'] <= current_abs_time <= w_obj['end']:
                    active_idx = i
                    break
            
            # Create Frame
            img = Image.new('RGBA', (W, H), (0,0,0,0))
            draw = ImageDraw.Draw(img)
            
            start_y = 20 + stroke_width
            
            start_y = 20 + stroke_width
            shadow_offset = (4, 4)
            shadow_color = (0, 0, 0, 160)

            # Pass 1: Shadows
            current_baseline_y = start_y + ascent # First line baseline
            
            for line_info in lines:
                line_w = line_info['width']
                current_x = (W - line_w) / 2
                for word_idx in line_info['words']:
                    pwm = processed_words[word_idx]
                    self._draw_text_with_spacing(
                        draw,
                        (current_x + shadow_offset[0], current_baseline_y + shadow_offset[1]),
                        pwm['text'],
                        font,
                        shadow_color,
                        letter_spacing,
                        stroke_width=stroke_width,
                        stroke_fill=shadow_color,
                        anchor='ls'
                    )
                    current_x += pwm['width'] + space_width
                
                current_baseline_y += line_height + vertical_spacing

            # Pass 2: Main Text
            current_baseline_y = start_y + ascent
            for line_info in lines:
                line_w = line_info['width']
                current_x = (W - line_w) / 2
                
                for word_idx in line_info['words']:
                    pwm = processed_words[word_idx]
                    
                    is_active = (word_idx == active_idx)
                    fill_c = active_color if is_active else inactive_color
                    
                    self._draw_text_with_spacing(
                        draw,
                        (current_x, current_baseline_y),
                        pwm['text'],
                        font,
                        fill_c,
                        letter_spacing,
                        stroke_width=stroke_width,
                        stroke_fill=stroke_color,
                        anchor='ls'
                    )
                    
                    current_x += pwm['width'] + space_width
                
                current_baseline_y += line_height + vertical_spacing
            
            # Update cache
            last_render["t"] = t
            last_render["img"] = img
            return img

        def make_frame(t):
            img = render_rgba(t)
            # Return RGB part (H, W, 3)
            return np.array(img.convert('RGB')) 
            # Note: convert('RGB') drops alpha and puts black background if transparent?
            # actually we want the color channels as they are. 
            # If we just do np.array(img)[:,:,:3], that's raw RGB. 
            # If the background is (0,0,0,0), RGB is (0,0,0). Correct.
            return np.array(img)[:, :, :3]

        def make_mask(t):
            img = render_rgba(t)
            # Return Alpha channel normalized 0-1 (H, W)
            # Alpha is index 3
            return np.array(img)[:, :, 3] / 255.0
            
        # Create VideoClip
        clip = VideoClip(make_frame, duration=duration)
        
        # Create Mask Clip
        mask_clip = VideoClip(make_mask, duration=duration, ismask=True)
        clip = clip.set_mask(mask_clip)
        
        clip = clip.set_start(start_time).set_end(end_time)
        return clip

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
