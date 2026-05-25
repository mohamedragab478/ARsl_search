import os
import sys
import re
import pandas as pd
import numpy as np
import imageio
import cv2
import torch
import gradio as gr
from sentence_transformers import SentenceTransformer, util
from transformers import pipeline

# ضبط ترميز الإخراج ليدعم اللغة العربية والرموز التعبيرية في موجه الأوامر
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 1. الإعدادات المحلية
S_DATA_ROOT = "S:\\grad\\archive"
S_LABELS_PATH = "S:\\grad\\KARSL-502_Labels.xlsx"

if os.path.exists(S_DATA_ROOT) and os.path.exists(S_LABELS_PATH):
    DATA_ROOT = S_DATA_ROOT
    LABELS_PATH = S_LABELS_PATH
    print(f"📊 تم العثور على البيانات في بارتشن S: {DATA_ROOT}")
else:
    DATA_ROOT = "data"
    LABELS_PATH = "KARSL-502_Labels.xlsx"
    print(f"📊 يتم استخدام المجلد المحلي للبيانات: {DATA_ROOT}")

MODEL_NAME = "intfloat/multilingual-e5-large-instruct"
OUTPUT_GIF = "result_sentence.gif"

# حد أدنى للتشابه - لو النتيجة أقل من كده يعتبرها "مش لاقي"
# موديلات E5 عادة تعطي تقييمات بين 0.8 و 1.0، فالحد المناسب هو 0.920 تقريباً
SIMILARITY_THRESHOLD = 0.920

# 2. قاموس مرادفات عربي لإثراء البحث الدلالي
# كل إشارة ممكن يكون ليها كلمات مرادفة أو أشكال مختلفة
ARABIC_SYNONYMS = {
    # الأرقام
    "0": ["صفر", "لا شيء"],
    "1": ["واحد", "أول"],
    "2": ["اثنان", "اتنين", "ثاني"],
    "3": ["ثلاثة", "تلاته", "ثالث"],
    "4": ["أربعة", "اربعه", "رابع"],
    "5": ["خمسة", "خمسه", "خامس"],
    "6": ["ستة", "سته", "سادس"],
    "7": ["سبعة", "سبعه", "سابع"],
    "8": ["ثمانية", "تمانيه", "ثامن"],
    "9": ["تسعة", "تسعه", "تاسع"],
    "10": ["عشرة", "عشره", "عاشر"],
    # التحيات والتواصل
    "السلام عليكم": ["سلام", "مرحبا", "أهلا", "تحية", "هاي", "صباح الخير", "مساء الخير"],
    "شكرا": ["شكراً", "ممنون", "أشكرك", "تسلم", "مشكور", "الله يعطيك العافية"],
    "من فضلك": ["لو سمحت", "أرجوك", "رجاء", "بليز"],
    "آسف": ["أسف", "عفوا", "معذرة", "سامحني", "اعتذر", "آسفة"],
    "نعم": ["أيوه", "ايوا", "صح", "تمام", "ماشي", "موافق", "اه"],
    "لا": ["لأ", "مش موافق", "رفض", "ابداً"],
    # العائلة
    "أب": ["بابا", "والد", "أبي", "الوالد", "أبوي", "ابويا"],
    "أم": ["ماما", "والدة", "أمي", "الوالدة", "أمي"],
    "أخ": ["أخوي", "شقيق"],
    "أخت": ["شقيقة", "أختي"],
    "جد": ["جدي", "سيدي"],
    "جدة": ["جدتي", "ستي", "تيتا", "نانا"],
    "ابن": ["ولد", "ابني", "ولدي"],
    "ابنة": ["بنت", "بنتي", "ابنتي"],
    "عائلة": ["أسرة", "أهل", "عيلة", "عيلتي"],
    "زوج": ["جوز", "ريل", "زوجي"],
    "زوجة": ["مرة", "حرمة", "زوجتي", "مراتي"],
    "طفل": ["بيبي", "رضيع", "صغير", "نونو"],
    "توأم": ["توأمين", "تؤام"],
    "رجل": ["راجل", "ذكر"],
    "شاب": ["شب", "فتى", "يافع"],
    "شابة": ["فتاة", "بنت", "آنسة"],
    "حفيد": ["حفيدي"],
    "زواج": ["عرس", "فرح", "عقد قران", "جواز"],
    "حمل": ["حامل", "حبلى"],
    "ولادة": ["وضع", "إنجاب"],
    "عم": ["عمي", "عمو"],
    "عمة": ["عمتي"],
    "خال": ["خالي", "خالو"],
    "خالة": ["خالتي"],
    "طلاق": ["انفصال", "تطليق"],
    "خطوبة": ["خطبة", "ملكة"],
    "حفلة": ["احتفال", "مناسبة", "سهرة"],
    "وفاة": ["موت", "فقدان", "رحيل", "توفي"],
    # الصفات
    "جميل": ["حلو", "وسيم", "جذاب", "حسن"],
    "قبيح": ["وحش", "بشع", "مش حلو"],
    "طويل": ["عالي", "مرتفع القامة"],
    "قصير": ["قصيرة", "صغير القامة"],
    "نحيف": ["رفيع", "نحيل", "ضعيف"],
    "سمين": ["تخين", "بدين", "ممتلئ"],
    "غني": ["ثري", "موسر", "ميسور"],
    "فقير": ["محتاج", "مسكين", "معدم"],
    "كبير": ["ضخم", "عظيم", "كبيرة"],
    "صغير": ["ضئيل", "زغير", "صغيرة"],
    # المشاعر
    "سعيد": ["فرحان", "مبسوط", "سعيدة", "مسرور"],
    "حزين": ["زعلان", "مكتئب", "حزينة", "متضايق"],
    "خائف": ["خايف", "مرعوب", "قلقان"],
    "غاضب": ["زعلان", "معصب", "غضبان", "متنرفز"],
    "متعب": ["تعبان", "مرهق", "مجهد"],
    # الأمراض والصحة
    "صداع": ["وجع راس", "ألم في الرأس", "راسي بيوجعني"],
    "ألم": ["وجع", "أوجاع", "بيوجعني"],
    "حمى": ["سخونة", "سخونية", "حرارة"],
    "زكام": ["رشح", "برد", "أنفلونزا", "إنفلونزا"],
    "إسهال": ["استفراغ"],
    "إمساك": ["إمساك"],
    "سرطان": ["ورم خبيث"],
    "طبيب": ["دكتور", "حكيم", "طبيبة", "دكتورة"],
    "ممرضة": ["ممرض", "مسعف", "مسعفة"],
    "مستشفى": ["مشفى", "مستوصف", "عيادة"],
    "دواء": ["علاج", "حبوب", "أدوية"],
    "التهاب": ["التهابات", "ورم"],
    "حساسية": ["تحسس"],
    # التعليم
    "معلم / مدرس": ["أستاذ", "مدرسة", "معلمة", "بروفيسور", "مدرس"],
    "مدرسة": ["مدرسه", "مؤسسة تعليمية", "روضة"],
    "جامعة": ["كلية", "معهد", "الجامعة"],
    "كتاب": ["مجلد", "مؤلف", "قصة"],
    "قلم": ["أقلام"],
    "طالب": ["تلميذ", "متعلم", "دارس", "طالبة"],
    "امتحان": ["اختبار", "تقييم", "كويز"],
    # المهن
    "طباخ": ["شيف", "طاهي", "طباخة"],
    "فلاح": ["مزارع", "فلاحة"],
    "موظف": ["عامل", "موظفة"],
    "صيدلي": ["صيدلاني", "صيدلية", "صيدلانية"],
    "محام": ["محامي", "محامية", "مستشار قانوني"],
    # الأماكن
    "بيت": ["منزل", "دار", "شقة", "بيتي", "مسكن"],
    "مسجد": ["جامع", "مصلى"],
    "سوق": ["محل", "دكان", "متجر", "مول"],
    # الضمائر
    "أنا": ["انا", "نفسي"],
    "أنت": ["انت", "إنت"],
    "أنتِ": ["انتي", "إنتي"],
    "هو": ["هوا", "هوه"],
    "هي": ["هيا", "هيه"],
    "نحن": ["احنا", "إحنا", "حنا"],
    "أنتم": ["انتو", "إنتو", "انتم"],
    "هم": ["هما", "همه"],
    # الأفعال الشائعة
    "أحب": ["بحب", "حب", "أعشق", "يحب", "بعشق"],
    "أكره": ["بكره", "كره", "يكره"],
    "أريد": ["عايز", "عاوز", "أبغى", "ابي", "يريد", "بدي"],
    "أعرف": ["بعرف", "عارف", "يعرف", "فاهم"],
    "أفهم": ["بفهم", "فاهم", "يفهم"],
    "آكل": ["باكل", "أكل", "ياكل", "يأكل", "بوكل"],
    "أشرب": ["بشرب", "شرب", "يشرب"],
    "أنام": ["بنام", "نوم", "ينام", "رقاد"],
    "أمشي": ["بمشي", "مشي", "يمشي", "سير"],
    "أجلس": ["بقعد", "قعود", "جلوس", "اقعد"],
    "أكتب": ["بكتب", "كتابة", "يكتب"],
    "أقرأ": ["بقرا", "قراءة", "يقرأ"],
    # الطعام
    "ماء": ["مية", "ميه", "مويه", "ماي"],
    "خبز": ["عيش", "توست"],
    "حليب": ["لبن", "حليب"],
    "أرز": ["رز"],
    "فاكهة": ["فواكه", "فاكهه"],
    "خضار": ["خضروات", "خضرة"],
    # الوقت
    "يوم": ["نهار", "يومي"],
    "ليل": ["ليلة", "مساء"],
    "صباح": ["صبح", "الصبح"],
    "أمس": ["امبارح", "البارحة"],
    "غداً": ["بكرة", "بكرا", "باكر"],
    "الآن": ["دلوقتي", "هسه", "حالياً", "توا"],
}

# 3. وظيفة تجذيع عربي بسيطة (Arabic Light Stemming)
def arabic_light_stem(word):
    """إزالة البادئات واللواحق الشائعة من الكلمات العربية"""
    if not isinstance(word, str) or len(word) < 3:
        return word

    original = word

    # إزالة أل التعريف
    if word.startswith("ال") and len(word) > 4:
        word = word[2:]

    # إزالة البادئات الشائعة (حروف المضارعة + الباء + الواو + الفاء)
    prefixes = ["وال", "بال", "فال", "لل", "وب", "وي", "وت", "ون",
                "فب", "في", "فت", "فن", "سي", "ست", "سن", "سأ",
                "و", "ف", "ب", "ل", "ي", "ت", "ن", "أ", "س"]
    for prefix in prefixes:
        if word.startswith(prefix) and len(word) - len(prefix) >= 2:
            word = word[len(prefix):]
            break

    # إزالة اللواحق الشائعة
    suffixes = ["ات", "ون", "ين", "ان", "تي", "ها", "هم", "هن",
                "كم", "كن", "نا", "ية", "ة", "ه", "ي", "ك"]
    for suffix in suffixes:
        if word.endswith(suffix) and len(word) - len(suffix) >= 2:
            word = word[:-len(suffix)]
            break

    return word if len(word) >= 2 else original

# 4. وظيفة لتنظيف النص العربي (محسّنة)
def normalize_arabic(text):
    if not isinstance(text, str): return ""
    text = re.sub("[إأآا]", "ا", text)
    text = re.sub("ى", "ي", text)
    text = re.sub("ؤ", "ء", text)
    text = re.sub("ئ", "ء", text)
    text = re.sub("ة", "ه", text)
    text = re.sub("گ", "ك", text)
    # إزالة التشكيل
    text = re.sub("[\u0610-\u061A\u064B-\u065F\u0670]", "", text)
    return text.strip()

# 5. بناء نص غني لكل إشارة (اسم الإشارة + مرادفات + الإنجليزي)
def build_enriched_corpus(labels_df):
    """بناء corpus غني بالمرادفات والمعاني لتحسين دقة البحث الدلالي"""
    enriched_texts = []

    for _, row in labels_df.iterrows():
        arabic = str(row.get("Sign-Arabic", ""))
        english = str(row.get("Sign-English", ""))
        arabic_norm = normalize_arabic(arabic)

        # البحث عن مرادفات للإشارة
        synonyms = []
        # البحث في القاموس بالنص الأصلي
        if arabic in ARABIC_SYNONYMS:
            synonyms = ARABIC_SYNONYMS[arabic]
        # البحث بالنص المنظف
        elif arabic_norm in ARABIC_SYNONYMS:
            synonyms = ARABIC_SYNONYMS[arabic_norm]
        else:
            # محاولة البحث بجزء من النص (لو فيه / يعني بدائل)
            for part in arabic.split("/"):
                part = part.strip()
                if part in ARABIC_SYNONYMS:
                    synonyms.extend(ARABIC_SYNONYMS[part])
                part_norm = normalize_arabic(part)
                if part_norm in ARABIC_SYNONYMS:
                    synonyms.extend(ARABIC_SYNONYMS[part_norm])

        # بناء النص الغني
        parts = [arabic_norm]
        if english and english.lower() != "nan":
            parts.append(english.lower())
        if synonyms:
            parts.extend([normalize_arabic(s) for s in synonyms])

        enriched_text = " ".join(parts)
        enriched_texts.append(enriched_text)

    return enriched_texts

# 6. بناء فهرس للفيديوهات (يدعم المجلدات الهرمية والمجلدات المسطحة)
def build_sign_video_index(data_root):
    index = {}
    if not os.path.exists(data_root):
        return index

    # محاولة البحث عن البنية المحلية المسطحة أولاً: data_root/<sign_id>/*.mp4
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

    # إذا لم تكن بنية مسطحة، نبحث في البنية الهرمية للأرشيف الكامل:
    # data_root/<speaker>/<camera>/<split>/<sign_id>/<sample_folder>
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

    # ترتيب العينات لضمان التناسق
    for k in index:
        index[k] = sorted(index[k])

    return index

# 7. وظيفة لاستخراج الإطارات (Frames) من فيديو أو مجلد صور أو ملف GIF
def get_video_frames(video_path, max_frames=25):
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
            print(f"❌ Error loading GIF {video_path}: {e}")
            return []
            
    if os.path.isdir(video_path):
        frames = []
        image_files = [os.path.join(video_path, f) for f in os.listdir(video_path)
                       if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        image_files = sorted(image_files)
        n_images = len(image_files)
        if n_images == 0:
            return []

        # اختيار إطارات موزعة بالتساوي
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

# 8. تحميل الموديل والبيانات
print("🔄 جاري تجهيز النظام...")
labels_df = pd.read_excel(LABELS_PATH)
labels_df['SignID'] = labels_df['SignID'].astype(str).str.zfill(4)

GIF_DATA_ROOT = "data_gifs"
USE_GIF_DATASET = os.path.exists(GIF_DATA_ROOT) and any(f.endswith('.gif') for f in os.listdir(GIF_DATA_ROOT))

if USE_GIF_DATASET:
    print(f"✅ تم العثور على قاعدة بيانات الـ GIFs المحسنة في: {GIF_DATA_ROOT}")
    video_index = {}
    for filename in os.listdir(GIF_DATA_ROOT):
        if filename.endswith(".gif"):
            sign_id = filename.split(".")[0]
            video_index[sign_id] = [os.path.join(GIF_DATA_ROOT, filename)]
else:
    video_index = build_sign_video_index(DATA_ROOT)

embed_model = SentenceTransformer(model_name_or_path=MODEL_NAME, device='cuda' if torch.cuda.is_available() else 'cpu')
print("🔄 جاري تحميل نموذج التعرف على الأسماء (NER)...")
ner_pipeline = pipeline("ner", model="hatmimoha/arabic-ner", aggregation_strategy="simple", device=0 if torch.cuda.is_available() else -1)

# بناء corpus غني بالمرادفات
labels_df["arabic_norm"] = labels_df["Sign-Arabic"].apply(normalize_arabic)
labels_df["english_norm"] = labels_df["Sign-English"].fillna("").str.lower()
enriched_corpus = build_enriched_corpus(labels_df)

# استخدام instruction واضح للموديل (E5 instruct format)
corpus_instruction = "passage: Arabic sign language label with synonyms and translation: "
corpus_with_prefix = [f"{corpus_instruction}{text}" for text in enriched_corpus]
corpus_embeddings = embed_model.encode(corpus_with_prefix, convert_to_tensor=True, normalize_embeddings=True)

print(f"✅ تم تحميل {len(labels_df)} إشارة مع embeddings غنية بالمرادفات")

# تحديد الإشارات التي هي حروف أبجدية فقط
# نستخدم الاسم الإنجليزي للتمييز بين الحروف والكلمات القصيرة الحقيقية
# مثلاً: "أم" (mother) كلمة حقيقية، لكن "ح" (Haa) حرف أبجدي
ARABIC_LETTER_ENGLISH_NAMES = {
    "alef", "baa", "ta", "thaa", "jeem", "Haa", "haa", "khaa",
    "daal", "thaal", "raa", "zay", "seen", "sheen", "Saad", "Daad",
    "Taa", "Zaa", "ain", "ghain", "faa", "qaaf", "kaaf", "laam",
    "meem", "noon", "waw", "yaa", "hamza", "Al",
    # أسماء بديلة
    "alif", "ba", "tha", "jim", "ha", "kha", "dal", "ra", "za",
    "sin", "shin", "sad", "dad", "ta_marbuta", "ayn", "ghayn",
    "fa", "qaf", "kaf", "lam", "mim", "nun", "ya",
}
alphabet_indices = set()
for i, row in labels_df.iterrows():
    arabic_label = str(row.get("Sign-Arabic", "")).strip()
    english_label = str(row.get("Sign-English", "")).strip().lower()
    # حرف أبجدي لو: النص العربي قصير (1-2 حرف) والاسم الإنجليزي يشبه اسم حرف
    is_single_arabic_char = len(arabic_label) <= 2 and not arabic_label.isdigit()
    is_letter_name = english_label in {n.lower() for n in ARABIC_LETTER_ENGLISH_NAMES}
    if is_single_arabic_char and is_letter_name:
        alphabet_indices.add(i)
print(f"📝 تم تحديد {len(alphabet_indices)} إشارة حروف أبجدية")

# بناء قاموس الحروف للتهجئة (Finger-spelling) للأسماء والكلمات المجهولة
char_to_id = {}
for _, row in labels_df.iterrows():
    arabic_char = str(row['Sign-Arabic']).strip()
    if len(arabic_char) == 1 and not arabic_char.isdigit():
        char_to_id[arabic_char] = row['SignID']

# 9. وظيفة البحث المحسّن عن كلمة واحدة
def semantic_search_word(word):
    """بحث دلالي محسّن عن كلمة واحدة مع دعم المرادفات والتجذيع"""
    word_norm = normalize_arabic(word)
    
    # بناء query غني - الكلمة الأصلية + المنظفة + بدون أل التعريف
    query_variants = set([word, word_norm])
    
    # محاولة العثور على الكلمة كمرادف وإضافة الكلمة الأساسية
    # مثلا لو الكلمة "انا"، المفتاح الأساسي هو "أنا"
    for main_key, synonyms in ARABIC_SYNONYMS.items():
        if word in synonyms or word_norm in synonyms:
            query_variants.add(main_key)
            query_variants.add(normalize_arabic(main_key))
            
    # إزالة أل التعريف فقط (بدون تجذيع عنيف)
    if word_norm.startswith("ال") and len(word_norm) > 3:
        query_variants.add(word_norm[2:])
    # إضافة الجذع للمساعدة
    word_stemmed = arabic_light_stem(word_norm)
    if len(word_stemmed) >= 3:
        query_variants.add(word_stemmed)
    
    query_text = " ".join(query_variants)

    # استخدام instruction واضح للموديل
    query_instruction = "query: Find the Arabic sign language gesture for the word: "
    query_with_prefix = f"{query_instruction}{query_text}"

    # البحث
    query_embedding = embed_model.encode([query_with_prefix], convert_to_tensor=True, normalize_embeddings=True)
    scores = util.cos_sim(query_embedding, corpus_embeddings)[0].clone()

    # معاقبة الحروف الأبجدية لما الكلمة المدخلة أطول من حرفين
    # عشان الحروف المفردة ما تتغلبش على الكلمات الحقيقية
    query_is_word = len(word_norm) > 2
    if query_is_word:
        for alpha_idx in alphabet_indices:
            scores[alpha_idx] *= 0.85  # تقليل score الحروف بـ 15%

    # ترتيب النتائج
    top_k = min(5, len(scores))
    top_results = torch.topk(scores, k=top_k)

    best_score = float(top_results.values[0])
    best_idx = int(top_results.indices[0])

    return best_idx, best_score, top_results

# 10. وظيفة تحليل الجملة واستخراج تفاصيل المطابقة
def get_sentence_analysis(sentence):
    # استخدام نموذج NER لاستخراج أسماء الأشخاص من الجملة
    ner_results = ner_pipeline(sentence)
    person_names = set()
    for entity in ner_results:
        if 'PERS' in entity.get('entity_group', '') or 'PERS' in entity.get('entity', ''):
            for w in re.findall(r'\w+', entity['word']):
                person_names.add(w)

    words = re.findall(r'\w+', sentence)
    analysis = []
    
    for word in words:
        item = {
            "word": word,
            "is_person": word in person_names,
            "is_matched": False,
            "best_id": None,
            "label_ar": "",
            "label_en": "",
            "score": 0.0,
            "score_pct": "0.0%"
        }
        
        if not item["is_person"]:
            best_idx, best_score, top_results = semantic_search_word(word)
            best_row = labels_df.iloc[best_idx]
            
            if best_score >= SIMILARITY_THRESHOLD:
                item["is_matched"] = True
                item["best_id"] = best_row['SignID']
                item["label_ar"] = best_row['Sign-Arabic']
                item["label_en"] = best_row['Sign-English']
                item["score"] = best_score
                item["score_pct"] = f"{best_score:.1%}"
                
        analysis.append(item)
        
    return analysis

# 11. واجهة Gradio
MAX_REVIEW_WORDS = 15

with gr.Blocks() as demo:
    gr.Markdown("# 🤟 مترجم جمل لغة الإشارة (Sentence to Sign)")
    gr.Markdown(
        "اكتب جملة كاملة وسنقوم بتركيب الإشارات وراء بعضها.\n\n"
        "💡 **النظام يفهم المعنى** — جرّب كتابة كلمات بالعامية أو مرادفات وهيتعرف عليها!"
    )

    sentence_state = gr.State([])

    with gr.Row():
        with gr.Column():
            input_text = gr.Textbox(
                label="اكتب الجملة هنا",
                placeholder="مثلاً: انا بحب الجامعة، أو: الدكتور راح المشفى"
            )
            with gr.Row():
                submit_btn = gr.Button("🔍 تحليل الجملة", variant="primary")
                threshold_slider = gr.Slider(
                    minimum=0.85, maximum=0.98, value=SIMILARITY_THRESHOLD, step=0.01,
                    label="حد التشابه (Threshold)",
                    info="قلّل القيمة لنتائج أكثر، زوّدها لنتائج أدق"
                )
            
            with gr.Column(visible=False) as review_column:
                gr.Markdown("### 📋 تفاصيل الكلمات المترجمة:")
                gr.Markdown("⚠️ *قم بإلغاء تحديد الكلمة إذا كنت ترغب في تهجئتها حرفاً بحرف بدلاً من الإشارة الدلالية.*")
                
                word_checkboxes = []
                for i in range(MAX_REVIEW_WORDS):
                    cb = gr.Checkbox(label="", visible=False, value=True)
                    word_checkboxes.append(cb)
                
                generate_btn = gr.Button("🎬 توليد فيديو لغة الإشارة", variant="success")

        with gr.Column():
            output_gif = gr.Image(label="الجملة بلغة الإشارة")
            output_log = gr.Textbox(label="تفاصيل الكلمات المترجمة", lines=8, visible=False)

    def process_analysis(sentence, threshold):
        global SIMILARITY_THRESHOLD
        SIMILARITY_THRESHOLD = threshold

        if not sentence.strip():
            updates = [gr.update(visible=False) for _ in range(MAX_REVIEW_WORDS)]
            yield [[]] + updates + [gr.update(visible=False)]
            return

        # Yield a loading placeholder first to keep the browser responsive
        loading_updates = [gr.update(visible=False) for _ in range(MAX_REVIEW_WORDS)]
        yield [[]] + loading_updates + [gr.update(visible=True)]

        analysis = get_sentence_analysis(sentence)

        updates = []
        for i in range(MAX_REVIEW_WORDS):
            if i < len(analysis):
                item = analysis[i]
                if item["is_person"]:
                    label = f"🔤 '{item['word']}' → اسم شخص (تهجئة تلقائية)"
                    val = False
                    interactive = False
                elif item["is_matched"]:
                    label = f"✔️ '{item['word']}' → مطابقة لـ '{item['label_ar']}' ({item['label_en']}) [{item['score_pct']}]"
                    val = True
                    interactive = True
                else:
                    label = f"❌ '{item['word']}' → كلمة مجهولة (تهجئة تلقائية)"
                    val = False
                    interactive = False
                updates.append(gr.update(label=label, visible=True, value=val, interactive=interactive))
            else:
                updates.append(gr.update(visible=False, value=False))

        yield [analysis] + updates + [gr.update(visible=True)]

    def process_generation(analysis_state, *checkbox_values):
        if not analysis_state:
            return None, gr.update(value="يرجى كتابة جملة وتحليلها أولاً.", visible=True)
        
        all_sentence_frames = []
        found_words_info = []
        
        for i, item in enumerate(analysis_state):
            word = item["word"]
            approved = checkbox_values[i] if i < len(checkbox_values) else False
            
            if approved and item["is_matched"]:
                best_id = item["best_id"]
                if best_id in video_index:
                    video_to_use = video_index[best_id][0]
                    frames = get_video_frames(video_to_use)
                    if frames:
                        all_sentence_frames.extend(frames)
                        found_words_info.append(
                            f"✅ '{word}' → {item['label_ar']} ({item['label_en']}) [{item['score_pct']}]"
                        )
                    else:
                        found_words_info.append(f"❌ '{word}' → {item['label_ar']} (لم يتم العثور على ملف إشارة)")
                else:
                    found_words_info.append(f"❌ '{word}' → {item['label_ar']} (غير متاح في الفهرس)")
            else:
                # Finger-spelling fallback
                spelled_chars = []
                has_valid_chars = False
                for char in word:
                    char_id = char_to_id.get(char)
                    if not char_id:
                        clean_char = normalize_arabic(char)
                        char_id = char_to_id.get(clean_char)
                    
                    if char_id and char_id in video_index:
                        video_to_use = video_index[char_id][0]
                        frames = get_video_frames(video_to_use)
                        if frames:
                            all_sentence_frames.extend(frames)
                            spelled_chars.append(char)
                            has_valid_chars = True
                
                if has_valid_chars:
                    spelling_str = " - ".join(spelled_chars)
                    reason = "اسم شخص" if item["is_person"] else ("تهجئة الكلمة الأصلية" if item["is_matched"] else "كلمة مجهولة")
                    found_words_info.append(
                        f"🔤 '{word}' → تم تهجئته: ({spelling_str}) [{reason}]"
                    )
                else:
                    found_words_info.append(f"❌ '{word}' - لم نتمكن من تهجئة الكلمة أو العثور على إشارة لها")
                    
        if all_sentence_frames:
            imageio.mimsave(OUTPUT_GIF, all_sentence_frames, fps=12, loop=0)
            result_msg = "\n".join(found_words_info)
            return OUTPUT_GIF, gr.update(value=result_msg, visible=True)
        else:
            result_msg = "\n".join(found_words_info) if found_words_info else "لم يتم العثور على أي إشارات للكلمات المكتوبة."
            return None, gr.update(value=result_msg, visible=True)

    # Wiring events
    submit_btn.click(
        fn=process_analysis,
        inputs=[input_text, threshold_slider],
        outputs=[sentence_state] + word_checkboxes + [review_column]
    )
    input_text.submit(
        fn=process_analysis,
        inputs=[input_text, threshold_slider],
        outputs=[sentence_state] + word_checkboxes + [review_column]
    )
    
    generate_btn.click(
        fn=process_generation,
        inputs=[sentence_state] + word_checkboxes,
        outputs=[output_gif, output_log]
    )

if __name__ == "__main__":
    demo.queue()
    demo.launch(share=False, theme=gr.themes.Soft())
