import logging
import os
import time
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import phrases
from .embeddings import build_embedder
from .generator import PoseGenerator, StubGenerator
from .inference_log import InferenceLog, clean_origin
from .model_provider import create_provider
from .motion_generator import MotionPlayback
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

logger = logging.getLogger("sinaliza")

app = FastAPI(title="Sinaliza API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

vocabulary = Vocabulary.load()
threshold = os.environ.get("SINALIZA_APPROX_THRESHOLD")
text_to_gloss = TextToGloss(
    vocabulary,
    build_embedder(),
    float(threshold) if threshold else None,
    # "false": palavra do vocabulário nunca é descartada pelo modelo (só as desconhecidas).
    model_discards_known=os.environ.get("SINALIZA_MODEL_DISCARDS_KNOWN", "true").lower() != "false",
)

# ML nosso: o classificador T1 (manter ou descartar cada palavra) vem do MLflow, em segundo plano.
model_provider = create_provider(dict(os.environ))
model_provider.start()
inference_log = InferenceLog(
    os.environ.get("SINALIZA_LOG_DATABASE_URL"),
    os.environ.get("SINALIZA_LOG_TEXT", "false").lower() == "true",
)


def create_generator(motions_path: str | None) -> PoseGenerator:
    """`MotionPlayback` se `motions_path` apontar para um arquivo de movimentos; senão o stub.

    Arquivo ausente ou inválido **não derruba a API**: cai no stub e avisa no log (e a
    resposta traz `generator: "stub"`, para a interface avisar que a animação é de teste).
    """
    if not motions_path:
        return StubGenerator()
    try:
        generator = MotionPlayback.load(Path(motions_path))
    except (OSError, ValueError, KeyError) as error:
        logger.warning("movimentos indisponíveis em %s (%s); usando o stub", motions_path, error)
        return StubGenerator()
    logger.info("movimentos carregados de %s: %d sinais", motions_path, len(generator.motions))
    return generator


generator: PoseGenerator = create_generator(os.environ.get("SINALIZA_MOTIONS"))


@app.get("/health")
def health() -> dict[str, str | bool]:
    """`model` mostra qual decide as palavras agora; `carregando` enquanto o modelo ainda não chegou."""
    classifier = model_provider.get()
    if classifier is not None:
        model = classifier.version
    elif model_provider.enabled:
        model = "lista-fixa (carregando o modelo)"
    else:
        model = "lista-fixa"
    return {"status": "ok", "contract_version": "1", "mock": False, "model": model}


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
def translate(
    request: TranslateRequest,
    background: BackgroundTasks,
    x_origem: str | None = Header(default=None),
) -> TranslateResponse:
    started = time.perf_counter()
    classifier = model_provider.get()
    decisions = None
    if classifier is not None:
        try:
            decisions = classifier.decide(request.text)
        except Exception:
            logger.exception("falha no classificador; usando a lista fixa nesta requisição")
    matches = text_to_gloss.resolve(request.text, decisions)
    if not matches:
        raise HTTPException(status_code=422, detail="o texto não contém palavras")
    glosses = TextToGloss.glosses(matches)
    if not glosses:
        raise HTTPException(
            status_code=422,
            detail=f"nenhuma palavra do texto tem sinal no vocabulário ({len(vocabulary.signs)} sinais)",
        )
    try:
        pose = generator.generate(glosses)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    latency_ms = round((time.perf_counter() - started) * 1000)
    used_model = decisions is not None
    model_version = classifier.version if used_model else "lista-fixa"
    background.add_task(
        inference_log.record,
        text=request.text,
        matches=matches,
        model_version=model_version,
        used_model=used_model,
        latency_ms=latency_ms,
        origin=clean_origin(x_origem),
    )
    return TranslateResponse(
        text=request.text,
        glosses=glosses,
        matches=[WordMatch(**vars(m)) for m in matches],
        generator=generator.name,
        pose=pose,
        model_version=model_version,
        latency_ms=latency_ms,
    )
