import os
import hashlib
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import OUTPUT_DIR, GIF_DATA_ROOT
from app.engine import engine
from app.schemas import (
    AnalysisRequest, AnalysisResponse, 
    GenerationRequest, GenerationResponse, 
    SignItem
)

# Load engine on startup and clean up if needed
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Server] Initializing Arabic Sign Language Search engine models...")
    try:
        engine.initialize()
        print("[Server] Engine ready!")
    except Exception as e:
        print(f"[Server] Failed to initialize engine: {e}")
    yield
    print("[Server] Shutting down ArSL Search server...")

app = FastAPI(
    title="Arabic Sign Language Search API",
    description="Backend API for mapping Arabic text sentences to Arabic Sign Language (ArSL) video sequences.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(req: AnalysisRequest):
    """Analyzes a sentence, run NER, and perform semantic search for each word."""
    try:
        results = engine.analyze_sentence(req.sentence, req.threshold)
        return {"words": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/generate", response_model=GenerationResponse)
async def generate(req: GenerationRequest):
    """
    Generates a combined GIF of ArSL signs. Caches output based on instructions.
    """
    try:
        # Create a unique hash of request params for caching
        serialized = json.dumps(
            [{"word": w.word, "use_sign": w.use_sign, "sign_id": w.sign_id} for w in req.words] + [req.fps],
            sort_keys=True
        )
        h = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        filename = f"{h}.gif"
        output_filepath = os.path.join(OUTPUT_DIR, filename)

        word_requests = [w.model_dump() for w in req.words]
        success, words_info = engine.generate_sentence_gif(word_requests, output_filepath, fps=req.fps)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to synthesize any sign language frames.")

        gif_url = f"/output/{filename}"
        return {
            "success": True,
            "gif_url": gif_url,
            "words_info": words_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.get("/api/signs", response_model=list[SignItem])
async def get_signs():
    """Returns the list of all available signs in the system."""
    try:
        if not engine.is_initialized:
            engine.initialize()
            
        signs = []
        for _, row in engine.labels_df.iterrows():
            sign_id = row['SignID']
            ar_label = str(row.get("Sign-Arabic", ""))
            signs.append({
                "sign_id": sign_id,
                "label_ar": ar_label,
                "label_en": str(row.get("Sign-English", "")),
                "has_gif": sign_id in engine.video_index,
                "synonyms": engine.get_synonyms_for_sign(ar_label)
            })
        return signs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch signs: {str(e)}")

# Mount static directories
# Output directory containing generated GIFs
if os.path.exists(OUTPUT_DIR):
    app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# GIF source database (so UI can directly display dictionary GIFs)
if os.path.exists(GIF_DATA_ROOT):
    app.mount("/data_gifs", StaticFiles(directory=GIF_DATA_ROOT), name="data_gifs")

# Serve the static frontend SPA
# Ensure folder exists
os.makedirs("app/static", exist_ok=True)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
