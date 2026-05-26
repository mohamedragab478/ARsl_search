from pydantic import BaseModel
from typing import List, Optional, Any

class AnalysisRequest(BaseModel):
    sentence: str
    threshold: Optional[float] = 0.920

class WordAnalysisResult(BaseModel):
    word: str
    is_person: bool
    is_matched: bool
    best_id: Optional[str] = None
    label_ar: str
    label_en: str
    score: float
    score_pct: str

class AnalysisResponse(BaseModel):
    words: List[WordAnalysisResult]

class GenerateWordItem(BaseModel):
    word: str
    use_sign: bool
    sign_id: Optional[str] = None

class GenerationRequest(BaseModel):
    words: List[GenerateWordItem]
    fps: Optional[int] = 12

class GenerationResponse(BaseModel):
    success: bool
    gif_url: Optional[str] = None
    words_info: List[Any]

class SignItem(BaseModel):
    sign_id: str
    label_ar: str
    label_en: str
    has_gif: bool
    synonyms: Optional[List[str]] = None
