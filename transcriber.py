from faster_whisper import WhisperModel
import os
from typing import List, Dict, Any
from settings import WHISPER_MODEL_SIZE

class Transcriber:
    def __init__(self, model_size: str = WHISPER_MODEL_SIZE, device: str = "cpu", compute_type: str = "int8"):
        """
        Initialize faster-whisper model.
        For Apple Silicon (M1/M2), device="cpu" and compute_type="int8" (quantization) often yields
        the best balance of speed and compatibility without specific CoreML hackery which can be unstable.
        """
        print(f"Loading Whisper model: {model_size} on {device} with {compute_type}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe_video(self, video_path: str) -> List[Dict[str, Any]]:
        """
        Transcribes video and returns a structure suitable for the Data Editor and Renderer.
        """
        print(f"Transcribing {video_path}...")
        # vad_filter=True helps remove silence
        segments, info = self.model.transcribe(video_path, vad_filter=True, word_timestamps=True)
        
        if not segments:
            return []

        # 1. Collect all words from all segments
        all_words = []
        for segment in segments:
            if segment.words:
                all_words.extend(segment.words)
            else:
                # If no word timestamps, we can't regroup accurately by words.
                # Fallback: create a dummy word object for the whole segment text
                # This ensures we don't lose data if model fails to timestamp words
                all_words.append({
                    "word": segment.text.strip(),
                    "start": segment.start,
                    "end": segment.end,
                    "probability": 1.0
                })
        
        # 2. Regroup into chunks of max N words
        MAX_WORDS_PER_SEGMENT = 3
        results = []
        
        # Iterate in chunks of MAX_WORDS_PER_SEGMENT
        for i in range(0, len(all_words), MAX_WORDS_PER_SEGMENT):
            chunk = all_words[i : i + MAX_WORDS_PER_SEGMENT]
            
            if not chunk:
                continue
                
            # Calculate new segment bounds
            start_time = chunk[0].start
            end_time = chunk[-1].end
            
            # Combine text
            # chunk items are objects with .word attribute if from whisper, 
            # OR dicts if we did the fallback above. 
            # faster-whisper words are usually objects. Let's handle both.
            
            chunk_words_data = []
            text_parts = []
            
            for w in chunk:
                # Handle faster-whisper Word object vs dict fallback
                if isinstance(w, dict):
                    w_text = w['word']
                    w_start = w['start']
                    w_end = w['end']
                    w_prob = w['probability']
                else:
                    w_text = w.word
                    w_start = w.start
                    w_end = w.end
                    w_prob = w.probability
                
                text_parts.append(w_text.strip())
                chunk_words_data.append({
                    "word": w_text,
                    "start": w_start,
                    "end": w_end,
                    "probability": w_prob
                })
            
            combined_text = " ".join(text_parts)
            
            results.append({
                "start": start_time,
                "end": end_time,
                "text": combined_text,
                "words": chunk_words_data
            })
            
        return results
