import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import phrases
from .embeddings import build_embedder
from .generator import PoseGenerator, StubGenerator
from .schemas import (
    CategoriesResponse,
    SignInfo,
    TranslateRequest,
    TranslateResponse,
    VocabularyResponse,
    WordMatch,
)
from .text_to_gloss import TextToGloss
from .vocabulary import Vocabulary

app = FastAPI(title="Sinaliza API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

vocabulary = Vocabulary.load()
threshold = os.environ.get("SINALIZA_APPROX_THRESHOLD")
text_to_gloss = TextToGloss(
    vocabulary, build_embedder(), float(threshold) if threshold else None
)
generator: PoseGenerator = StubGenerator()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/vocabulary", response_model=VocabularyResponse)
def get_vocabulary() -> VocabularyResponse:
    return VocabularyResponse(
        signs=[
            SignInfo(gloss=s.gloss, forms=list(s.forms), contexts=list(s.contexts), note=s.note)
            for s in vocabulary.signs
        ]
    )


@app.get("/categories", response_model=CategoriesResponse)
def get_categories() -> CategoriesResponse:
    return CategoriesResponse(categories=phrases.load())


@app.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest) -> TranslateResponse:
    matches = text_to_gloss.resolve(request.text)
    if not matches:
        raise HTTPException(status_code=422, detail="o texto não contém palavras")
    glosses = TextToGloss.glosses(matches)
    if not glosses:
        raise HTTPException(
            status_code=422,
            detail=f"nenhuma palavra do texto tem sinal no vocabulário ({len(vocabulary.signs)} sinais)",
        )
    return TranslateResponse(
        text=request.text,
        glosses=glosses,
        matches=[WordMatch(**vars(m)) for m in matches],
        pose=generator.generate(glosses),
    )
