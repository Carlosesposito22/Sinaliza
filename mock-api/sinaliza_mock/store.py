"""Progresso e gamificação em memória (some ao reiniciar o mock). Regras da v2 do contrato (regra, não ML).

Quando a API real assumir `/learn/*`, estas regras valem como especificação; mudá-las exige
atualizar docs/contrato-api-web.md.

Temas e prova:
- Só o primeiro tema começa aberto; o próximo abre quando a prova do anterior é aprovada.
- Dentro do tema, as aulas abrem em ordem. Com todas feitas, a prova abre.
- Prova com nota >= PASS_SCORE: tema aprovado (XP da prova só na primeira aprovação).
- Prova reprovada (num tema ainda não aprovado): começa uma nova "rodada". Todas as aulas do tema
  voltam a ficar pendentes (abertas, sem ordem) e a prova só reabre quando todas forem refeitas.
- Tema já aprovado pode refazer aulas e prova à vontade; reprovar depois não fecha nada.

Treino fora da trilha (só com sinais do vocabulário curado):
- Revisão: cada exercício errado numa aula, e cada sinal errado na prova, põe o sinal na fila de revisão.
  A sessão de revisão pega os mais errados (até REVIEW_MAX_SIGNS); acertar todos os exercícios de um
  sinal na sessão o tira da fila.
- Desafio do dia: CHALLENGE_SIGNS sinais sorteados (a mesma sorte o dia todo) entre os que a pessoa já
  viu em aulas. XP extra só na primeira vez que passa no dia.
"""

import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from .achievements import Achievement, Stats, catalog
from .content import PASS_SCORE, XP_PER_EXAM, Content
from .grading import exam_score, grade_answer
from .schemas import (
    AchievementInfo,
    AchievementsResponse,
    CompleteRequest,
    DictionaryEntry,
    DictionaryResponse,
    ExamResult,
    ExamSubmit,
    LessonProgress,
    LessonResult,
    Practice,
    PracticeResult,
    Progress,
    QuestionResult,
    SignCheck,
    ThemeProgress,
)

PASS_ACCURACY = 0.6  # aula: acerto mínimo para contar como feita
XP_PER_LEVEL = 100
DAILY_GOAL_XP = 20
PERFECT_BONUS_XP = 5
PRACTICE_PASS = 0.6
XP_REVIEW = 10
XP_CHALLENGE = 15
REVIEW_MAX_SIGNS = 5
CHALLENGE_SIGNS = 5


@dataclass
class ThemeState:
    round: int = 0  # sobe a cada prova reprovada; aula só conta se feita na rodada atual
    attempts: int = 0
    best_score: float = 0.0
    last_score: float | None = None
    passed: bool = False
    first_try: bool = False  # aprovado na primeira tentativa
    comeback: bool = False  # aprovado depois de reprovar


@dataclass
class LessonState:
    stars: int = 0
    best_accuracy: float = 0.0
    completions: int = 0
    round: int = -1  # rodada do tema em que a aula foi feita pela última vez


@dataclass
class State:
    xp: int = 0
    streak: int = 0
    best_streak: int = 0
    last_date: date | None = None
    xp_by_date: dict[date, int] = field(default_factory=dict)
    lessons: dict[str, LessonState] = field(default_factory=dict)
    themes: dict[str, ThemeState] = field(default_factory=dict)
    achievements: dict[str, date] = field(default_factory=dict)  # id → data em que ganhou
    weak: dict[str, int] = field(default_factory=dict)  # glosa → erros ainda na fila de revisão
    reviews_done: int = 0
    challenges_done: int = 0
    challenge_dates: set[date] = field(default_factory=set)


@dataclass
class Session:
    """Uma sessão de treino em andamento (revisão ou desafio). Some ao ser concluída."""

    id: str
    learner_id: str
    kind: str
    glosses: list[str]
    exercise_ids: set[str]


def stars_for(accuracy: float) -> int:
    if accuracy < PASS_ACCURACY:
        return 0
    if accuracy >= 0.9:
        return 3
    if accuracy >= 0.75:
        return 2
    return 1


class Store:
    def __init__(self, content: Content):
        self.content = content
        self.learners: dict[str, State] = {}
        self.catalog: list[Achievement] = catalog([(t.id, t.title) for t in content.themes])
        self.sessions: dict[str, Session] = {}
        self._next_session = 0

    def reset(self, learner_id: str) -> None:
        self.learners.pop(learner_id, None)

    def _state(self, learner_id: str) -> State:
        return self.learners.setdefault(learner_id, State())

    # ------------------------------------------------------------ leitura

    def progress(self, learner_id: str, today: date) -> Progress:
        state = self._state(learner_id)
        themes: dict[str, ThemeProgress] = {}
        lessons: dict[str, LessonProgress] = {}
        previous_passed = True
        for theme_id in self.content.theme_order:
            theme = state.themes.get(theme_id, ThemeState())
            open_theme = previous_passed or theme.passed
            redo_round = theme.round > 0 and not theme.passed
            previous_done = True
            done_count = 0
            lesson_ids = self.content.theme_lessons[theme_id]
            for lesson_id in lesson_ids:
                record = state.lessons.get(lesson_id)
                done = bool(record and record.round == theme.round)
                if not open_theme:
                    status = "locked"
                elif done:
                    status = "completed"
                elif redo_round or previous_done:
                    status = "available"
                else:
                    status = "locked"
                done_count += done
                lessons[lesson_id] = LessonProgress(
                    status=status,
                    stars=record.stars if record else 0,
                    best_accuracy=record.best_accuracy if record else 0.0,
                    completions=record.completions if record else 0,
                    needs_redo=open_theme and redo_round and not done,
                )
                previous_done = done
            all_done = done_count == len(lesson_ids)
            if not open_theme:
                theme_status = "locked"
            elif theme.passed:
                theme_status = "passed"
            elif all_done:
                theme_status = "exam_ready"
            else:
                theme_status = "learning"
            themes[theme_id] = ThemeProgress(
                status=theme_status,
                lessons_completed=done_count,
                lessons_total=len(lesson_ids),
                exam_attempts=theme.attempts,
                best_exam_score=theme.best_score,
                last_exam_score=theme.last_score,
                must_redo=redo_round and not all_done,
            )
            previous_passed = theme.passed

        streak = state.streak
        if state.last_date and state.last_date < today - timedelta(days=1):
            streak = 0
        xp_today = state.xp_by_date.get(today, 0)
        return Progress(
            learner_id=learner_id,
            xp=state.xp,
            level=1 + state.xp // XP_PER_LEVEL,
            xp_in_level=state.xp % XP_PER_LEVEL,
            xp_to_next_level=XP_PER_LEVEL - state.xp % XP_PER_LEVEL,
            streak_days=streak,
            best_streak=state.best_streak,
            daily_goal_xp=DAILY_GOAL_XP,
            xp_today=xp_today,
            goal_reached_today=xp_today >= DAILY_GOAL_XP,
            last_activity_date=state.last_date.isoformat() if state.last_date else None,
            themes=themes,
            lessons=lessons,
            review_signs=len(state.weak),
            challenge_available=bool(self._seen_glosses(state)),
            challenge_done_today=today in state.challenge_dates,
        )

    def exam_open(self, learner_id: str, theme_id: str, today: date) -> bool:
        return self.progress(learner_id, today).themes[theme_id].status in ("exam_ready", "passed")

    def exam_seed(self, learner_id: str, theme_id: str) -> str:
        """Muda a cada tentativa: a ordem das questões não se repete igual."""
        theme = self._state(learner_id).themes.get(theme_id, ThemeState())
        return f"{learner_id}:{theme_id}:{theme.attempts}"

    # ------------------------------------------------------------ conquistas

    def _stats(self, state: State, progress: Progress) -> Stats:
        themes = state.themes.values()
        return Stats(
            lessons_done=sum(1 for r in state.lessons.values() if r.completions > 0),
            perfect_lessons=sum(1 for r in state.lessons.values() if r.best_accuracy >= 1),
            exams_taken=sum(t.attempts for t in themes),
            themes_passed=sum(1 for t in themes if t.passed),
            perfect_exams=sum(1 for t in themes if t.best_score >= 1),
            first_try_passes=sum(1 for t in themes if t.first_try),
            comebacks=sum(1 for t in themes if t.comeback),
            passed_theme_ids=frozenset(tid for tid, t in state.themes.items() if t.passed),
            best_streak=state.best_streak,
            level=progress.level,
            reviews_done=state.reviews_done,
            challenges_done=state.challenges_done,
        )

    def _info(self, item: Achievement, state: State, stats: Stats) -> AchievementInfo:
        done, current = item.check(stats)
        when = state.achievements.get(item.id)
        return AchievementInfo(
            id=item.id, title=item.title, description=item.description, kind=item.kind, tier=item.tier,
            category=item.category, icon=item.icon, unlocked=when is not None,
            unlocked_at=when.isoformat() if when else None, current=current, target=item.target,
        )

    def _award(self, state: State, progress: Progress, today: date) -> list[AchievementInfo]:
        """Guarda as conquistas recém-alcançadas e as devolve (para o front comemorar)."""
        stats = self._stats(state, progress)
        new: list[AchievementInfo] = []
        for item in self.catalog:
            if item.id not in state.achievements and item.check(stats)[0]:
                state.achievements[item.id] = today
                new.append(self._info(item, state, stats))
        return new

    def achievements(self, learner_id: str, today: date) -> AchievementsResponse:
        state = self._state(learner_id)
        stats = self._stats(state, self.progress(learner_id, today))
        items = [self._info(item, state, stats) for item in self.catalog]
        return AchievementsResponse(
            unlocked_count=sum(i.unlocked for i in items), total=len(items), achievements=items
        )

    # ------------------------------------------------------------ escrita

    def _gain(self, state: State, xp: int, today: date) -> None:
        """Soma XP e conta o dia para a sequência."""
        state.xp += xp
        state.xp_by_date[today] = state.xp_by_date.get(today, 0) + xp
        if state.last_date != today:
            continues = state.last_date == today - timedelta(days=1)
            state.streak = state.streak + 1 if continues else 1
            state.best_streak = max(state.best_streak, state.streak)
        state.last_date = today

    def complete(self, learner_id: str, lesson_id: str, request: CompleteRequest, today: date) -> LessonResult:
        lesson = self.content.lessons[lesson_id]
        theme_id = self.content.lesson_theme[lesson_id]
        before = self.progress(learner_id, today)
        state = self._state(learner_id)

        accuracy = request.correct / request.total
        passed = accuracy >= PASS_ACCURACY
        stars = stars_for(accuracy)
        perfect = request.correct == request.total
        xp_gained = round(lesson.xp_reward * accuracy) + (PERFECT_BONUS_XP if perfect else 0) if passed else 0

        for ex_id in request.mistakes:
            if ex_id.startswith(f"{lesson_id}-"):
                self._mark_weak(state, self.content.exercise_targets.get(ex_id, []))

        if passed:
            record = state.lessons.setdefault(lesson_id, LessonState())
            record.stars = max(record.stars, stars)
            record.best_accuracy = round(max(record.best_accuracy, accuracy), 4)
            record.completions += 1
            record.round = state.themes.get(theme_id, ThemeState()).round
            self._gain(state, xp_gained, today)

        after = self.progress(learner_id, today)
        new_achievements = self._award(state, after, today)
        unlocked = [
            lid for lid, item in after.lessons.items()
            if item.status == "available" and before.lessons[lid].status == "locked"
        ]
        return LessonResult(
            passed=passed,
            accuracy=round(accuracy, 4),
            stars=stars,
            xp_gained=xp_gained,
            bonus_perfect=passed and perfect,
            level_up=after.level > before.level,
            goal_reached_now=not before.goal_reached_today and after.goal_reached_today,
            unlocked_lesson_ids=unlocked,
            exam_unlocked=before.themes[theme_id].status == "learning" and after.themes[theme_id].status == "exam_ready",
            new_achievements=new_achievements,
            progress=after,
        )

    def submit_exam(self, learner_id: str, theme_id: str, request: ExamSubmit, today: date) -> ExamResult:
        before = self.progress(learner_id, today)
        state = self._state(learner_id)
        theme = state.themes.setdefault(theme_id, ThemeState())
        answers = {a.question_id: a.text for a in request.answers}

        questions: list[QuestionResult] = []
        for item in self.content.exams[theme_id]:
            answer = answers.get(item.id, "")
            grade = grade_answer(answer, item.glosses, self.content.accept_table, item.expected_text)
            questions.append(
                QuestionResult(
                    question_id=item.id,
                    kind=item.kind,
                    glosses=item.glosses,
                    expected_text=item.expected_text,
                    answer=answer,
                    score=grade.score,
                    signs=[SignCheck(gloss=s.gloss, word=self.content.word(s.gloss), correct=s.correct) for s in grade.signs],
                    extra_words=grade.extra_words,
                )
            )
        for q in questions:
            self._mark_weak(state, [c.gloss for c in q.signs if not c.correct])
        score = exam_score([q.score for q in questions])
        passed = score >= PASS_SCORE
        first_pass = passed and not theme.passed

        theme.attempts += 1
        theme.last_score = score
        theme.best_score = round(max(theme.best_score, score), 4)
        xp_gained = XP_PER_EXAM if first_pass else 0
        must_redo: list[str] = []
        if first_pass:
            theme.passed = True
            theme.first_try = theme.attempts == 1
            theme.comeback = theme.attempts > 1
            self._gain(state, xp_gained, today)
        elif not passed and not theme.passed:
            theme.round += 1
            must_redo = list(self.content.theme_lessons[theme_id])

        after = self.progress(learner_id, today)
        new_achievements = self._award(state, after, today)
        unlocked = [
            tid for tid, item in after.themes.items()
            if item.status != "locked" and before.themes[tid].status == "locked"
        ]
        return ExamResult(
            passed=passed,
            score=score,
            pass_score=PASS_SCORE,
            xp_gained=xp_gained,
            level_up=after.level > before.level,
            goal_reached_now=not before.goal_reached_today and after.goal_reached_today,
            questions=questions,
            unlocked_theme_ids=unlocked,
            must_redo_lesson_ids=must_redo,
            new_achievements=new_achievements,
            progress=after,
        )

    # ------------------------------------------------------------ treino: revisão, desafio, dicionário

    def _mark_weak(self, state: State, glosses: list[str]) -> None:
        for gloss in glosses:
            state.weak[gloss] = state.weak.get(gloss, 0) + 1

    def _seen_glosses(self, state: State) -> list[str]:
        """Sinais das aulas que a pessoa já fez ao menos uma vez, na ordem da trilha."""
        seen: list[str] = []
        for lesson_id, record in state.lessons.items():
            if record.completions > 0:
                seen += [g for g in self.content.lesson_glosses[lesson_id] if g not in seen]
        return seen

    def _session(self, learner_id: str, kind: str, title: str, xp: int, glosses: list[str], per_sign: int, seed: str,
                 completed_today: bool = False) -> Practice:
        self._next_session += 1
        session_id = f"{kind}-{self._next_session}"
        exercises = self.content.practice_exercises(session_id, glosses, seed, per_sign)
        self.sessions[session_id] = Session(session_id, learner_id, kind, glosses, {e.id for e in exercises})
        return Practice(id=session_id, kind=kind, title=title, xp_reward=xp, glosses=glosses, exercises=exercises,
                        completed_today=completed_today)

    def review(self, learner_id: str) -> Practice | None:
        state = self._state(learner_id)
        if not state.weak:
            return None
        glosses = sorted(state.weak, key=lambda g: (-state.weak[g], g))[:REVIEW_MAX_SIGNS]
        return self._session(learner_id, "review", "Revisão dos erros", XP_REVIEW, glosses, 2,
                             f"{learner_id}:review:{state.reviews_done}")

    def challenge(self, learner_id: str, today: date) -> Practice | None:
        state = self._state(learner_id)
        seen = self._seen_glosses(state)
        if not seen:
            return None
        rng = random.Random(f"{learner_id}:{today.isoformat()}")
        glosses = rng.sample(seen, min(CHALLENGE_SIGNS, len(seen)))
        return self._session(learner_id, "challenge", "Desafio do dia", XP_CHALLENGE, glosses, 1,
                             f"{learner_id}:{today.isoformat()}", completed_today=today in state.challenge_dates)

    def complete_practice(self, learner_id: str, session_id: str, request: CompleteRequest, today: date) -> PracticeResult:
        session = self.sessions.pop(session_id)
        before = self.progress(learner_id, today)
        state = self._state(learner_id)
        accuracy = request.correct / request.total
        passed = accuracy >= PRACTICE_PASS

        missed: set[str] = set()
        for ex_id in request.mistakes:
            if ex_id in session.exercise_ids:
                missed |= set(self.content.exercise_targets.get(ex_id, []))
        cleared = [g for g in session.glosses if g not in missed and g in state.weak]
        for gloss in cleared:
            state.weak.pop(gloss)
        if session.kind == "challenge":
            self._mark_weak(state, sorted(missed))

        xp_gained = 0
        if passed and session.kind == "review":
            state.reviews_done += 1
            xp_gained = XP_REVIEW
        if passed and session.kind == "challenge" and today not in state.challenge_dates:
            state.challenge_dates.add(today)
            state.challenges_done += 1
            xp_gained = XP_CHALLENGE
        if xp_gained:
            self._gain(state, xp_gained, today)

        after = self.progress(learner_id, today)
        return PracticeResult(
            passed=passed,
            accuracy=round(accuracy, 4),
            xp_gained=xp_gained,
            level_up=after.level > before.level,
            goal_reached_now=not before.goal_reached_today and after.goal_reached_today,
            cleared_glosses=cleared,
            new_achievements=self._award(state, after, today),
            progress=after,
        )

    def dictionary(self, learner_id: str) -> DictionaryResponse:
        """Os 210 sinais do vocabulário curado, marcando os que a pessoa já viu nas aulas."""
        state = self._state(learner_id)
        seen = set(self._seen_glosses(state))
        entries = [
            DictionaryEntry(
                gloss=gloss,
                word=self.content.word(gloss),
                forms=list(sign["pt"]),
                theme_ids=self.content.themes_of(gloss),
                seen=gloss in seen,
                mistakes=state.weak.get(gloss, 0),
            )
            for gloss, sign in self.content.vocabulary.items()
        ]
        entries.sort(key=lambda e: (not e.seen, e.word))
        return DictionaryResponse(total=len(entries), seen_count=len(seen), signs=entries)

