import os
import re
import pandas as pd
import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline

from app.config import (
    LABELS_PATH, GIF_DATA_ROOT, DATA_ROOT, OUTPUT_DIR,
    MODEL_NAME, NER_MODEL_NAME, SIMILARITY_THRESHOLD,
    DEVICE, NER_DEVICE
)
from app.synonyms import ARABIC_SYNONYMS, ARABIC_LETTER_ENGLISH_NAMES
from app.utils import normalize_arabic, arabic_light_stem, get_video_frames, generate_gif

class ArslEngine:
    def __init__(self):
        self.labels_df = None
        self.video_index = {}
        self.embed_model = None
        self.ner_pipeline = None
        self.corpus_embeddings = None
        self.alphabet_indices = set()
        self.char_to_id = {}
        self.is_initialized = False

    def initialize(self):
        if self.is_initialized:
            return
        
        print("[Engine] Loading ArSL Search labels and building index...")
        if not os.path.exists(LABELS_PATH):
            raise FileNotFoundError(f"Label file not found: {LABELS_PATH}")

        # Load Excel file
        self.labels_df = pd.read_excel(LABELS_PATH)
        self.labels_df['SignID'] = self.labels_df['SignID'].astype(str).str.zfill(4)

        # Check if we should use flat GIF dataset
        use_gif_dataset = os.path.exists(GIF_DATA_ROOT) and any(f.endswith('.gif') for f in os.listdir(GIF_DATA_ROOT))
        if use_gif_dataset:
            print(f"[Engine] Enriched GIF dataset found at: {GIF_DATA_ROOT}")
            self.video_index = {}
            for filename in os.listdir(GIF_DATA_ROOT):
                if filename.endswith(".gif"):
                    sign_id = filename.split(".")[0]
                    self.video_index[sign_id] = [os.path.join(GIF_DATA_ROOT, filename)]
        else:
            print(f"[Engine] Scanning video dataset directory: {DATA_ROOT}")
            self.video_index = self._build_sign_video_index(DATA_ROOT)

        # Load embedding model
        print(f"[Engine] Loading SentenceTransformer model: {MODEL_NAME} on {DEVICE}...")
        self.embed_model = SentenceTransformer(model_name_or_path=MODEL_NAME, device=DEVICE)

        # Load NER pipeline
        print(f"[Engine] Loading Named Entity Recognition (NER) model: {NER_MODEL_NAME}...")
        self.ner_pipeline = pipeline(
            "ner", 
            model=NER_MODEL_NAME, 
            aggregation_strategy="simple", 
            device=NER_DEVICE
        )

        # Preprocess and enrich labels corpus
        self.labels_df["arabic_norm"] = self.labels_df["Sign-Arabic"].apply(normalize_arabic)
        self.labels_df["english_norm"] = self.labels_df["Sign-English"].fillna("").str.lower()
        
        enriched_corpus = self._build_enriched_corpus()
        
        corpus_instruction = "passage: Arabic sign language label with synonyms and translation: "
        corpus_with_prefix = [f"{corpus_instruction}{text}" for text in enriched_corpus]
        
        print("[Engine] Encoding enriched corpus...")
        self.corpus_embeddings = self.embed_model.encode(
            corpus_with_prefix, 
            convert_to_tensor=True, 
            normalize_embeddings=True
        )

        # Build alphabet indices & char_to_id map
        self._build_alphabet_helpers()
        
        self.is_initialized = True
        print(f"[Engine] ArSL Engine successfully initialized with {len(self.labels_df)} signs!")

    def _build_sign_video_index(self, data_root):
        """Indexes local video paths using hierarchical or flat structure."""
        index = {}
        if not os.path.exists(data_root):
            return index

        # Try flat search first: data_root/<sign_id>/*.mp4
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

    def _build_enriched_corpus(self):
        """Build synonym-enriched corpus strings."""
        enriched_texts = []

        for _, row in self.labels_df.iterrows():
            arabic = str(row.get("Sign-Arabic", ""))
            english = str(row.get("Sign-English", ""))
            arabic_norm = normalize_arabic(arabic)

            # Retrieve synonyms from dictionary
            synonyms = []
            if arabic in ARABIC_SYNONYMS:
                synonyms = ARABIC_SYNONYMS[arabic]
            elif arabic_norm in ARABIC_SYNONYMS:
                synonyms = ARABIC_SYNONYMS[arabic_norm]
            else:
                # Try parts
                for part in arabic.split("/"):
                    part = part.strip()
                    if part in ARABIC_SYNONYMS:
                        synonyms.extend(ARABIC_SYNONYMS[part])
                    part_norm = normalize_arabic(part)
                    if part_norm in ARABIC_SYNONYMS:
                        synonyms.extend(ARABIC_SYNONYMS[part_norm])

            # Combine parts
            parts = [arabic_norm]
            if english and english.lower() != "nan":
                parts.append(english.lower())
            if synonyms:
                parts.extend([normalize_arabic(s) for s in synonyms])

            enriched_texts.append(" ".join(parts))

        return enriched_texts

    def get_synonyms_for_sign(self, arabic):
        """Helper to get synonyms list for a specific Arabic sign label."""
        arabic_norm = normalize_arabic(arabic)
        synonyms = []
        if arabic in ARABIC_SYNONYMS:
            synonyms = ARABIC_SYNONYMS[arabic]
        elif arabic_norm in ARABIC_SYNONYMS:
            synonyms = ARABIC_SYNONYMS[arabic_norm]
        else:
            for part in arabic.split("/"):
                part = part.strip()
                if part in ARABIC_SYNONYMS:
                    synonyms.extend(ARABIC_SYNONYMS[part])
                part_norm = normalize_arabic(part)
                if part_norm in ARABIC_SYNONYMS:
                    synonyms.extend(ARABIC_SYNONYMS[part_norm])
        return list(set(synonyms))

    def _build_alphabet_helpers(self):
        """Build dictionary & sets for character spelling."""
        self.alphabet_indices = set()
        for i, row in self.labels_df.iterrows():
            arabic_label = str(row.get("Sign-Arabic", "")).strip()
            english_label = str(row.get("Sign-English", "")).strip().lower()
            
            is_single_arabic_char = len(arabic_label) <= 2 and not arabic_label.isdigit()
            is_letter_name = english_label in {n.lower() for n in ARABIC_LETTER_ENGLISH_NAMES}
            if is_single_arabic_char and is_letter_name:
                self.alphabet_indices.add(i)

        self.char_to_id = {}
        for _, row in self.labels_df.iterrows():
            arabic_char = str(row['Sign-Arabic']).strip()
            if len(arabic_char) == 1 and not arabic_char.isdigit():
                self.char_to_id[arabic_char] = row['SignID']

    def semantic_search_word(self, word):
        """Run semantic search for a single word, applying synonym expansions and spelling penalty."""
        if not self.is_initialized:
            self.initialize()

        word_norm = normalize_arabic(word)
        query_variants = {word, word_norm}

        # Add synonyms keys
        for main_key, synonyms in ARABIC_SYNONYMS.items():
            if word in synonyms or word_norm in synonyms:
                query_variants.add(main_key)
                query_variants.add(normalize_arabic(main_key))

        # Definite article removal
        if word_norm.startswith("ال") and len(word_norm) > 3:
            query_variants.add(word_norm[2:])
            
        # Stemming
        word_stemmed = arabic_light_stem(word_norm)
        if len(word_stemmed) >= 3:
            query_variants.add(word_stemmed)

        query_text = " ".join(query_variants)
        query_instruction = "query: Find the Arabic sign language gesture for the word: "
        query_with_prefix = f"{query_instruction}{query_text}"

        # Generate embedding and calculate similarity
        query_embedding = self.embed_model.encode([query_with_prefix], convert_to_tensor=True, normalize_embeddings=True)
        scores = util.cos_sim(query_embedding, self.corpus_embeddings)[0].clone()

        # Penalize alphabet letters when the input query word is longer than two characters
        if len(word_norm) > 2:
            for alpha_idx in self.alphabet_indices:
                scores[alpha_idx] *= 0.85

        # Pick best score
        best_score = float(torch.max(scores))
        best_idx = int(torch.argmax(scores))

        return best_idx, best_score

    def analyze_sentence(self, sentence, similarity_threshold=SIMILARITY_THRESHOLD):
        """Analyze sentence, identifying people's names and matching sign language words."""
        if not self.is_initialized:
            self.initialize()

        # Identify person entities using NER
        ner_results = self.ner_pipeline(sentence)
        person_names = set()
        for entity in ner_results:
            if 'PERS' in entity.get('entity_group', '') or 'PERS' in entity.get('entity', ''):
                for w in re.findall(r'\w+', entity['word']):
                    person_names.add(w)

        words = re.findall(r'\w+', sentence)
        analysis = []

        for word in words:
            is_person = word in person_names
            item = {
                "word": word,
                "is_person": is_person,
                "is_matched": False,
                "best_id": None,
                "label_ar": "",
                "label_en": "",
                "score": 0.0,
                "score_pct": "0.0%"
            }

            if not is_person:
                best_idx, best_score = self.semantic_search_word(word)
                if best_score >= similarity_threshold:
                    best_row = self.labels_df.iloc[best_idx]
                    item["is_matched"] = True
                    item["best_id"] = best_row['SignID']
                    item["label_ar"] = best_row['Sign-Arabic']
                    item["label_en"] = best_row['Sign-English']
                    item["score"] = best_score
                    item["score_pct"] = f"{best_score:.1%}"

            analysis.append(item)

        return analysis

    def generate_sentence_gif(self, word_requests, output_path, fps=12):
        """
        Synthesizes a combined GIF from sign language videos or character spelling fallbacks.
        word_requests: List of dicts, e.g. [{"word": "انا", "use_sign": True, "sign_id": "0123"}]
        """
        if not self.is_initialized:
            self.initialize()

        all_sentence_frames = []
        words_info = []

        for req in word_requests:
            word = req.get("word", "")
            use_sign = req.get("use_sign", False)
            sign_id = req.get("sign_id")

            # Try semantic sign language mapping
            if use_sign and sign_id and sign_id in self.video_index:
                video_to_use = self.video_index[sign_id][0]
                frames = get_video_frames(video_to_use)
                if frames:
                    all_sentence_frames.extend(frames)
                    words_info.append({
                        "word": word,
                        "type": "sign",
                        "status": "success",
                        "sign_id": sign_id
                    })
                else:
                    # Fallback to finger spelling if sign file is missing
                    use_sign = False

            # If not using sign or fallback triggered
            if not use_sign:
                spelled_chars = []
                has_valid_chars = False
                for char in word:
                    char_id = self.char_to_id.get(char)
                    if not char_id:
                        clean_char = normalize_arabic(char)
                        char_id = self.char_to_id.get(clean_char)
                    
                    if char_id and char_id in self.video_index:
                        video_to_use = self.video_index[char_id][0]
                        frames = get_video_frames(video_to_use)
                        if frames:
                            all_sentence_frames.extend(frames)
                            spelled_chars.append(char)
                            has_valid_chars = True
                
                if has_valid_chars:
                    words_info.append({
                        "word": word,
                        "type": "spelling",
                        "status": "success",
                        "spelled_chars": spelled_chars
                    })
                else:
                    words_info.append({
                        "word": word,
                        "type": "none",
                        "status": "failed",
                        "message": "Spelling/Sign not available"
                    })

        if all_sentence_frames:
            success = generate_gif(all_sentence_frames, output_path, fps=fps)
            return success, words_info
        else:
            return False, words_info

# Initialize singleton engine
engine = ArslEngine()
