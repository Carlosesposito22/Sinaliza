"""Mock da API do Sinaliza (contrato v2). Sobe na porta 8000, a mesma da API real.

Serve o tradutor com respostas falsas porém no formato final, e a trilha de aprendizado de
verdade (temas de data/trilha.json, aulas, prova, conquistas, revisão, desafio do dia e dicionário),
com progresso em memória. Só usa os 210 sinais do vocabulário curado.
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

from .content import Content, ROOT, load_signs, load_trilha
from .schemas import (
    CONTRACT_VERSION,
    CategoriesResponse,
    AchievementsResponse,
    CheckRequest,
    CheckResult,
    CompleteRequest,
    DictionaryResponse,
    Exam,
    ExamResult,
    ExamSubmit,
    Health,
    Lesson,
    LessonResult,
    PathResponse,
    Practice,
    PracticeResult,
    Progress,
    SignCheck,
    SignInfo,
    TranslateRequest,
    TranslateResponse,
    VocabularyResponse,
    WordMatch,
)
from .grading import grade_answer
from .store import Store

PHRASES = Path(os.environ.get("SINALIZA_PHRASES", ROOT / "data" / "phrases.json"))

app = FastAPI(title="Sinaliza API (mock)", version=f"contrato-{CONTRACT_VERSION}")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

signs = load_signs()
content = Content(load_trilha(), signs)
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
        raise HTTPException(status_code=409, detail="aula bloqueada: conclua a anterior (ou a prova do tema anterior) primeiro")
    return store.complete(who, lesson_id, request, today)


def known_theme(theme_id: str) -> str:
    if theme_id not in content.exams:
        raise HTTPException(status_code=404, detail=f"tema desconhecido: {theme_id}")
    return theme_id


EXAM_CLOSED = "prova bloqueada: conclua todas as aulas do tema primeiro"


@app.get("/learn/themes/{theme_id}/exam", response_model=Exam)
def learn_exam(
    theme_id: str,
    x_learner_id: str | None = Header(default=None),
    x_mock_today: str | None = Header(default=None),
) -> Exam:
    """As questões da prova, sem o gabarito: o avatar toca `glosses` e a pessoa escreve o que entendeu."""
    who = learner(x_learner_id)
    known_theme(theme_id)
    if not store.exam_open(who, theme_id, today_from(x_mock_today)):
        raise HTTPException(status_code=409, detail=EXAM_CLOSED)
    theme = next(t for t in content.themes if t.id == theme_id)
    return Exam(
        theme_id=theme_id,
        title=f"Prova: {theme.title}",
        pass_score=theme.exam.pass_score,
        questions=content.exam_questions(theme_id, store.exam_seed(who, theme_id)),
    )


@app.post("/learn/themes/{theme_id}/exam", response_model=ExamResult)
def learn_exam_submit(
    theme_id: str,
    request: ExamSubmit,
    x_learner_id: str | None = Header(default=None),
    x_mock_today: str | None = Header(default=None),
) -> ExamResult:
    """Corrige a prova (regra, não ML). Questão sem resposta vale 0."""
    who = learner(x_learner_id)
    today = today_from(x_mock_today)
    known_theme(theme_id)
    if not store.exam_open(who, theme_id, today):
        raise HTTPException(status_code=409, detail=EXAM_CLOSED)
    unknown = [a.question_id for a in request.answers if content.exam_item(theme_id, a.question_id) is None]
    if unknown:
        raise HTTPException(status_code=422, detail=f"questões que não são deste tema: {', '.join(unknown)}")
    return store.submit_exam(who, theme_id, request, today)


@app.get("/learn/achievements", response_model=AchievementsResponse)
def learn_achievements(
    x_learner_id: str | None = Header(default=None),
    x_mock_today: str | None = Header(default=None),
) -> AchievementsResponse:
    """Todas as conquistas (medalhas e troféus), ganhas ou não, com quanto falta para cada uma."""
    return store.achievements(learner(x_learner_id), today_from(x_mock_today))


@app.post("/learn/check", response_model=CheckResult)
def learn_check(request: CheckRequest) -> CheckResult:
    """Corrige uma resposta escrita de treino (`sign_to_text`) com a mesma regra da prova. Não grava nada."""
    unknown = [g for g in request.glosses if g not in content.vocabulary]
    if unknown:
        raise HTTPException(status_code=422, detail=f"sinais fora do vocabulário: {', '.join(unknown)}")
    grade = grade_answer(request.answer, request.glosses, content.accept_table, request.text)
    return CheckResult(
        correct=grade.score >= 1,
        score=grade.score,
        expected_text=request.text,
        signs=[SignCheck(gloss=s.gloss, word=content.word(s.gloss), correct=s.correct) for s in grade.signs],
        extra_words=grade.extra_words,
    )


@app.get("/learn/review", response_model=Practice)
def learn_review(x_learner_id: str | None = Header(default=None)) -> Practice:
    """Sessão de revisão com os sinais que a pessoa mais errou em aulas e provas."""
    session = store.review(learner(x_learner_id))
    if session is None:
        raise HTTPException(status_code=409, detail="nada para revisar: você não tem erros pendentes")
    return session


@app.get("/learn/challenge", response_model=Practice)
def learn_challenge(x_learner_id: str | None = Header(default=None), x_mock_today: str | None = Header(default=None)) -> Practice:
    """Desafio do dia: sinais sorteados entre os que a pessoa já viu (o mesmo sorteio o dia todo)."""
    session = store.challenge(learner(x_learner_id), today_from(x_mock_today))
    if session is None:
        raise HTTPException(status_code=409, detail="conclua uma aula primeiro: o desafio usa sinais que você já viu")
    return session


@app.post("/learn/practice/{session_id}/complete", response_model=PracticeResult)
def learn_practice_complete(
    session_id: str,
    request: CompleteRequest,
    x_learner_id: str | None = Header(default=None),
    x_mock_today: str | None = Header(default=None),
) -> PracticeResult:
    who = learner(x_learner_id)
    session = store.sessions.get(session_id)
    if session is None or session.learner_id != who:
        raise HTTPException(status_code=404, detail="sessão de treino desconhecida ou já concluída")
    return store.complete_practice(who, session_id, request, today_from(x_mock_today))


@app.get("/learn/dictionary", response_model=DictionaryResponse)
def learn_dictionary(x_learner_id: str | None = Header(default=None)) -> DictionaryResponse:
    """Os 210 sinais do vocabulário curado, com os que a pessoa já viu nas aulas marcados."""
    return store.dictionary(learner(x_learner_id))


@app.delete("/learn/progress", status_code=204)
def learn_reset(x_learner_id: str | None = Header(default=None)) -> Response:
    """Só no mock: zera o progresso de quem chamou (a API real pode não oferecer)."""
    store.reset(learner(x_learner_id))
    return Response(status_code=204)
