"""Mock da API do Sinaliza (contrato v1). Sobe na porta 8000, a mesma da API real.

Serve o tradutor com respostas falsas porém no formato final, e a trilha de aprendizado de
verdade (conteúdo do vocabulário curado e regras de gamificação), com progresso em memória.
Uso: uvicorn sinaliza_mock.server:app --port 8000   (docs interativos em /docs)
"""

import json
import os
import re
import time
import unicodedata
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .content import Content, ROOT, load_signs
from .schemas import (
    CONTRACT_VERSION,
    CategoriesResponse,
    CompleteRequest,
    Health,
    Lesson,
    LessonResult,
    PathResponse,
    Progress,
    SignInfo,
    TranslateRequest,
    TranslateResponse,
    VocabularyResponse,
    WordMatch,
)
from .store import Store

PHRASES = Path(os.environ.get("SINALIZA_PHRASES", ROOT / "data" / "phrases.json"))

app = FastAPI(title="Sinaliza API (mock)", version=f"contrato-{CONTRACT_VERSION}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

signs = load_signs()
content = Content(signs)
store = Store(content)

# Palavras funcionais que o mock descarta; a API real decide com o modelo de ML.
FUNCTION_WORDS = set(
    "a o as os um uma de do da dos das em no na nos nas por para com sem e ou que se ao aos "
    "eu tu ele ela nos voce voces me te meu minha seu sua é são foi está estou".split()
)


def fold(text: str) -> str:
    return unicodedata.normalize("NFC", text).casefold()


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", fold(text)) if unicodedata.category(c) != "Mn")


FORMS = {fold(form): sign["gloss"] for sign in signs for form in sign["pt"] if " " not in form}


def learner(x_learner_id: str | None) -> str:
    if not x_learner_id or not x_learner_id.strip():
        raise HTTPException(status_code=400, detail="envie o cabeçalho X-Learner-Id (um UUID gerado pelo front)")
    return x_learner_id.strip()


def today_from(x_mock_today: str | None) -> date:
    """`X-Mock-Today: AAAA-MM-DD` (só no mock) deixa testar sequência de dias sem esperar."""
    if not x_mock_today:
        return date.today()
    try:
        return date.fromisoformat(x_mock_today)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="X-Mock-Today deve ser AAAA-MM-DD") from error


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", contract_version=CONTRACT_VERSION, mock=True)


@app.get("/vocabulary", response_model=VocabularyResponse)
def get_vocabulary() -> VocabularyResponse:
    return VocabularyResponse(
        signs=[SignInfo(gloss=s["gloss"], forms=s["pt"], contexts=s["contexts"], note=s.get("note")) for s in signs]
    )


@app.get("/categories", response_model=CategoriesResponse)
def get_categories() -> CategoriesResponse:
    data = json.loads(PHRASES.read_text(encoding="utf-8"))
    return CategoriesResponse(categories=data["categories"])


@app.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest, response: Response) -> TranslateResponse:
    started = time.perf_counter()
    words = re.findall(r"[\wÀ-ÿ]+(?:-[\wÀ-ÿ]+)*", request.text)
    if not words:
        raise HTTPException(status_code=422, detail="o texto não contém palavras")
    matches: list[WordMatch] = []
    for word in words:
        gloss = FORMS.get(fold(word))
        if gloss:
            matches.append(WordMatch(word=word, gloss=gloss, kind="exact", score=1.0, decision="MANTER", probability=0.97))
        elif strip_accents(word) in FUNCTION_WORDS:
            matches.append(WordMatch(word=word, gloss=None, kind="function", score=0.0, decision="DESCARTAR", probability=0.04))
        else:
            matches.append(WordMatch(word=word, gloss=None, kind="ignored", score=0.0, decision="MANTER", probability=0.62))
    glosses = [m.gloss for m in matches if m.gloss]
    if not glosses:
        raise HTTPException(
            status_code=422,
            detail=f"nenhuma palavra do texto tem sinal no vocabulário ({len(signs)} sinais)",
        )
    response.headers["X-Sinaliza-Mock"] = "1"
    return TranslateResponse(
        text=request.text,
        glosses=glosses,
        matches=matches,
        generator="mock",
        pose=None,
        model_version="mock",
        latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
    )


@app.get("/learn/path", response_model=PathResponse)
def learn_path() -> PathResponse:
    return content.path()


@app.get("/learn/lessons/{lesson_id}", response_model=Lesson)
def learn_lesson(lesson_id: str) -> Lesson:
    lesson = content.lessons.get(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail=f"lição desconhecida: {lesson_id}")
    return lesson


@app.get("/learn/progress", response_model=Progress)
def learn_progress(x_learner_id: str | None = Header(default=None), x_mock_today: str | None = Header(default=None)) -> Progress:
    return store.progress(learner(x_learner_id), today_from(x_mock_today))


@app.post("/learn/lessons/{lesson_id}/complete", response_model=LessonResult)
def learn_complete(
    lesson_id: str,
    request: CompleteRequest,
    x_learner_id: str | None = Header(default=None),
    x_mock_today: str | None = Header(default=None),
) -> LessonResult:
    who = learner(x_learner_id)
    today = today_from(x_mock_today)
    if lesson_id not in content.lessons:
        raise HTTPException(status_code=404, detail=f"lição desconhecida: {lesson_id}")
    if store.progress(who, today).lessons[lesson_id].status == "locked":
        raise HTTPException(status_code=409, detail="lição bloqueada: conclua a anterior primeiro")
    return store.complete(who, lesson_id, request, today)


@app.delete("/learn/progress", status_code=204)
def learn_reset(x_learner_id: str | None = Header(default=None)) -> Response:
    """Só no mock: zera o progresso de quem chamou (a API real pode não oferecer)."""
    store.reset(learner(x_learner_id))
    return Response(status_code=204)
