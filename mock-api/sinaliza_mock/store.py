"""Progresso e gamificação em memória (some ao reiniciar o mock). Regras da v1 do contrato.

Quando a API real assumir `/learn/*`, estas regras valem como especificação; mudá-las exige
atualizar docs/contrato-api-web.md.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from .content import Content
from .schemas import CompleteRequest, LessonProgress, LessonResult, Progress

PASS_ACCURACY = 0.6
XP_PER_LEVEL = 100
DAILY_GOAL_XP = 20
PERFECT_BONUS_XP = 5


@dataclass
class State:
    xp: int = 0
    streak: int = 0
    best_streak: int = 0
    last_date: date | None = None
    xp_by_date: dict[date, int] = field(default_factory=dict)
    lessons: dict[str, dict] = field(default_factory=dict)


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

    def reset(self, learner_id: str) -> None:
        self.learners.pop(learner_id, None)

    def _state(self, learner_id: str) -> State:
        return self.learners.setdefault(learner_id, State())

    def progress(self, learner_id: str, today: date) -> Progress:
        state = self._state(learner_id)
        lessons: dict[str, LessonProgress] = {}
        previous_done = True
        for lesson_id in self.content.order:
            record = state.lessons.get(lesson_id)
            done = bool(record and record["completions"] > 0)
            status = "completed" if done else ("available" if previous_done else "locked")
            lessons[lesson_id] = LessonProgress(
                status=status,
                stars=record["stars"] if record else 0,
                best_accuracy=record["best_accuracy"] if record else 0.0,
                completions=record["completions"] if record else 0,
            )
            previous_done = done
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
            lessons=lessons,
        )

    def complete(self, learner_id: str, lesson_id: str, request: CompleteRequest, today: date) -> LessonResult:
        lesson = self.content.lessons[lesson_id]
        before = self.progress(learner_id, today)
        state = self._state(learner_id)

        accuracy = request.correct / request.total
        passed = accuracy >= PASS_ACCURACY
        stars = stars_for(accuracy)
        perfect = request.correct == request.total
        xp_gained = round(lesson.xp_reward * accuracy) + (PERFECT_BONUS_XP if perfect else 0) if passed else 0

        if passed:
            record = state.lessons.setdefault(lesson_id, {"stars": 0, "best_accuracy": 0.0, "completions": 0})
            record["stars"] = max(record["stars"], stars)
            record["best_accuracy"] = round(max(record["best_accuracy"], accuracy), 4)
            record["completions"] += 1
            state.xp += xp_gained
            state.xp_by_date[today] = state.xp_by_date.get(today, 0) + xp_gained
            if state.last_date != today:
                continues = state.last_date == today - timedelta(days=1)
                state.streak = state.streak + 1 if continues else 1
                state.best_streak = max(state.best_streak, state.streak)
            state.last_date = today

        after = self.progress(learner_id, today)
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
            progress=after,
        )
