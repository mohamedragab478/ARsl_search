import os
import torch

# Paths
LABELS_PATH = os.environ.get("ARSL_LABELS_PATH", "KARSL-502_Labels.xlsx")
GIF_DATA_ROOT = os.environ.get("ARSL_GIF_DATA_ROOT", "data_gifs")
DATA_ROOT = os.environ.get("ARSL_DATA_ROOT", "data")
OUTPUT_DIR = os.environ.get("ARSL_OUTPUT_DIR", "output")

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Model Settings
MODEL_NAME = "intfloat/multilingual-e5-large-instruct"
NER_MODEL_NAME = "hatmimoha/arabic-ner"
SIMILARITY_THRESHOLD = 0.920

# Hardware
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
NER_DEVICE = 0 if torch.cuda.is_available() else -1

print(f"[Config] Loaded - Device: {DEVICE}, Output Dir: {OUTPUT_DIR}")
