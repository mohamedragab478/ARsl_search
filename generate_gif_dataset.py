import os
import sys
import pandas as pd
import numpy as np
import cv2
import imageio

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

S_DATA_ROOT = "S:\\grad\\archive"
S_LABELS_PATH = "S:\\grad\\KARSL-502_Labels.xlsx"

if os.path.exists(S_DATA_ROOT) and os.path.exists(S_LABELS_PATH):
    DATA_ROOT = S_DATA_ROOT
    LABELS_PATH = S_LABELS_PATH
else:
    DATA_ROOT = "data"
    LABELS_PATH = "KARSL-502_Labels.xlsx"

print(f"📂 Data Root: {DATA_ROOT}")
print(f"📂 Labels Path: {LABELS_PATH}")

OUTPUT_DIR = "data_gifs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. build sign video index
def build_sign_video_index(data_root):
    index = {}
    if not os.path.exists(data_root):
        return index

    # Check flat local structure first: data_root/<sign_id>/*.mp4
    simple_found = False
    for item in os.listdir(data_root):
        item_path = os.path.join(data_root, item)
        if os.path.isdir(item_path):
            videos = [os.path.join(item_path, f) for f in os.listdir(item_path) if f.lower().endswith('.mp4')]
            if videos:
                index[item] = sorted(videos)
                simple_found = True

    if simple_found:
        return index

    # Hierarchical structure: data_root/<speaker>/<camera>/<split>/<sign_id>/<sample_folder>
    for speaker in os.listdir(data_root):
        speaker_path = os.path.join(data_root, speaker)
        if not os.path.isdir(speaker_path):
            continue
        for camera in os.listdir(speaker_path):
            camera_path = os.path.join(speaker_path, camera)
            if not os.path.isdir(camera_path):
                continue
            for split in os.listdir(camera_path):
                split_path = os.path.join(camera_path, split)
                if not os.path.isdir(split_path) or split not in ['train', 'test']:
                    continue
                for sign_id in os.listdir(split_path):
                    sign_path = os.path.join(split_path, sign_id)
                    if not os.path.isdir(sign_path):
                        continue

                    norm_sign_id = sign_id.zfill(4)
                    if norm_sign_id not in index:
                        index[norm_sign_id] = []

                    for sample in os.listdir(sign_path):
                        sample_path = os.path.join(sign_path, sample)
                        if os.path.isdir(sample_path):
                            index[norm_sign_id].append(sample_path)

    for k in index:
        index[k] = sorted(index[k])

    return index

def get_video_frames(video_path, max_frames=25):
    if os.path.isdir(video_path):
        frames = []
        image_files = [os.path.join(video_path, f) for f in os.listdir(video_path)
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        image_files = sorted(image_files)
        n_images = len(image_files)
        if n_images == 0:
            return []

        indices = np.linspace(0, n_images - 1, min(max_frames, n_images), dtype=int)
        for idx in indices:
            img = cv2.imread(image_files[idx])
            if img is not None:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = cv2.resize(img, (320, 240))
                frames.append(img)
        return frames
    else:
        cap = cv2.VideoCapture(video_path)
        frames = []
        count = 0
        while count < max_frames:
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (320, 240))
            frames.append(frame)
            count += 1
        cap.release()
        return frames

def main():
    if not os.path.exists(LABELS_PATH):
        print(f"❌ Excel label file not found: {LABELS_PATH}")
        sys.exit(1)

    labels_df = pd.read_excel(LABELS_PATH)
    labels_df['SignID'] = labels_df['SignID'].astype(str).str.zfill(4)
    
    print("🔄 Indexing videos...")
    video_index = build_sign_video_index(DATA_ROOT)
    
    if not video_index:
        print(f"❌ No videos found in {DATA_ROOT}")
        sys.exit(1)
        
    print(f"Found {len(video_index)} signs in dataset index.")
    
    success_count = 0
    for sign_id in labels_df['SignID'].unique():
        if sign_id not in video_index:
            print(f"⚠️ SignID {sign_id} not in video index, skipping.")
            continue
            
        dest_gif = os.path.join(OUTPUT_DIR, f"{sign_id}.gif")
        if os.path.exists(dest_gif):
            success_count += 1
            continue
            
        sample_path = video_index[sign_id][0]
        try:
            frames = get_video_frames(sample_path)
            if frames:
                imageio.mimsave(dest_gif, frames, fps=12, loop=0)
                success_count += 1
                if success_count % 50 == 0:
                    print(f"✅ Generated {success_count} GIFs...")
            else:
                print(f"⚠️ No frames found for SignID {sign_id}")
        except Exception as e:
            print(f"❌ Error generating GIF for SignID {sign_id}: {e}")

    print(f"🎉 Completed! Generated {success_count} GIFs under '{OUTPUT_DIR}' directory.")

if __name__ == "__main__":
    main()
