import os
import sys
import re
import gradio as gr
import imageio

# Set output encoding to support Arabic language
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Import core modular components
from app.config import SIMILARITY_THRESHOLD
from app.engine import engine

# Legacy global output path from original code
OUTPUT_GIF = "result_sentence.gif"

print("Initializing Gradio interface on new modular system...")

# Load models and label index
engine.initialize()

# Gradio Interface Constants
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
        if not sentence.strip():
            updates = [gr.update(visible=False) for _ in range(MAX_REVIEW_WORDS)]
            yield [[]] + updates + [gr.update(visible=False)]
            return

        # Yield a loading placeholder first to keep the browser responsive
        loading_updates = [gr.update(visible=False) for _ in range(MAX_REVIEW_WORDS)]
        yield [[]] + loading_updates + [gr.update(visible=True)]

        # Perform analysis via core engine
        analysis = engine.analyze_sentence(sentence, threshold)

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
        
        # Build requests payload for engine
        word_requests = []
        for i, item in enumerate(analysis_state):
            word = item["word"]
            approved = checkbox_values[i] if i < len(checkbox_values) else False
            word_requests.append({
                "word": word,
                "use_sign": approved and item["is_matched"],
                "sign_id": item.get("best_id")
            })

        # Generate output GIF using modular engine
        success, words_info = engine.generate_sentence_gif(word_requests, OUTPUT_GIF, fps=12)
        
        found_words_info = []
        for i, info in enumerate(words_info):
            w = info["word"]
            item = analysis_state[i]
            
            if info["type"] == "sign" and info["status"] == "success":
                found_words_info.append(
                    f"✅ '{w}' → {item['label_ar']} ({item['label_en']}) [{item['score_pct']}]"
                )
            elif info["type"] == "spelling" and info["status"] == "success":
                spelling_str = " - ".join(info["spelled_chars"])
                reason = "اسم شخص" if item["is_person"] else ("تهجئة الكلمة الأصلية" if item["is_matched"] else "كلمة مجهولة")
                found_words_info.append(
                    f"🔤 '{w}' → تم تهجئته: ({spelling_str}) [{reason}]"
                )
            else:
                found_words_info.append(f"❌ '{w}' - لم نتمكن من تهجئة الكلمة أو العثور على إشارة لها")
                    
        if success:
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