import os
import re
import cv2
import numpy as np
import imageio

def normalize_arabic(text):
    """Normalize Arabic characters to standard forms and remove Tashkeel."""
    if not isinstance(text, str):
        return ""
    text = re.sub("[إأآا]", "ا", text)
    text = re.sub("ى", "ي", text)
    text = re.sub("ؤ", "ء", text)
    text = re.sub("ئ", "ء", text)
    text = re.sub("ة", "ه", text)
    text = re.sub("گ", "ك", text)
    # Remove diacritics (Tashkeel)
    text = re.sub("[\u0610-\u061A\u064B-\u065F\u0670]", "", text)
    return text.strip()

def arabic_light_stem(word):
    """Remove common prefixes and suffixes from Arabic words to get a rough root/stem."""
    if not isinstance(word, str) or len(word) < 3:
        return word

    original = word

    # Remove 'Al' (the) definite article
    if word.startswith("ال") and len(word) > 4:
        word = word[2:]

    # Remove common prefixes (present tense letters + Baa + Waw + Faa)
    prefixes = ["وال", "بال", "فال", "لل", "وب", "وي", "وت", "ون",
                "فب", "في", "فت", "فن", "سي", "ست", "سن", "سأ",
                "و", "ف", "ب", "ل", "ي", "ت", "n", "أ", "س"]  # Wait, there was "n" or "ن"? The original script has "ن". Oh, wait, in sign_search.py it had "ن" but let me double-check.
    # Ah! The original script had:
    # prefixes = ["وال", "بال", "فال", "لل", "وب", "وي", "وت", "ون",
    #             "فب", "في", "فت", "فن", "سي", "ست", "سن", "سأ",
    #             "و", "ف", "ب", "ل", "ي", "ت", "ن", "أ", "س"]
    # Yes, it had "ن". Let's use the exact original to be consistent. Let's fix that.
    prefixes = ["وال", "بال", "فال", "لل", "وب", "وي", "وت", "ون",
                "فب", "في", "فت", "فن", "سي", "ست", "سن", "سأ",
                "و", "ف", "ب", "ل", "ي", "ت", "ن", "أ", "س"]

    for prefix in prefixes:
        if word.startswith(prefix) and len(word) - len(prefix) >= 2:
            word = word[len(prefix):]
            break

    # Remove common suffixes
    suffixes = ["ات", "ون", "ين", "ان", "تي", "ها", "هم", "هن",
                "كم", "كن", "نا", "ية", "ة", "ه", "ي", "ك"]
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            word = word[:-len(suffix)]
            break

    return word if len(word) >= 2 else original

def get_video_frames(video_path, max_frames=25):
    """Extract and resize frames from video files, folders, or GIFs."""
    # Check if it's a GIF
    if str(video_path).lower().endswith('.gif'):
        try:
            frames = imageio.mimread(video_path)
            resized_frames = []
            for frame in frames:
                # imageio.mimread returns RGB or RGBA depending on the GIF
                if len(frame.shape) == 3 and frame.shape[2] == 4:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)
                elif len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
                frame = cv2.resize(frame, (320, 240))
                resized_frames.append(frame)
            return resized_frames
        except Exception as e:
            print(f"[Utils] Error loading GIF {video_path}: {e}")
            return []
            
    # Check if it's a directory of images
    if os.path.isdir(video_path):
        frames = []
        image_files = [os.path.join(video_path, f) for f in os.listdir(video_path)
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        image_files = sorted(image_files)
        n_images = len(image_files)
        if n_images == 0:
            return []

        # Select evenly distributed frames
        indices = np.linspace(0, n_images - 1, min(max_frames, n_images), dtype=int)
        for idx in indices:
            img = cv2.imread(image_files[idx])
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (320, 240))
                frames.append(img)
        return frames
    else:
        # Standard video file
        cap = cv2.VideoCapture(video_path)
        frames = []
        count = 0
        while count < max_frames:
            ret, frame = cap.read()
            if not ret: 
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (320, 240))
            frames.append(frame)
            count += 1
        cap.release()
        return frames

def generate_gif(frames, output_path, fps=12):
    """Save a list of RGB frames as a looping GIF."""
    if not frames:
        return False
    try:
        imageio.mimsave(output_path, frames, fps=fps, loop=0)
        return True
    except Exception as e:
        print(f"[Utils] Error saving GIF to {output_path}: {e}")
        return False
