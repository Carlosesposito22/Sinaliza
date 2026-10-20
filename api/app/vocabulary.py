"""Vocabulário do MVP (data/vocabulary.json): sinais, formas em português e contextos."""

import json
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "vocabulary.json"


def slug(text: str) -> str:
    """Sem acento e em maiúsculas, como em data/ e model/."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper()


def vocabulary_path() -> Path:
    return Path(os.environ.get("SINALIZA_VOCABULARY", DEFAULT_PATH))


@dataclass(frozen=True)
class Sign:
    gloss: str
    forms: tuple[str, ...]
    contexts: tuple[str, ...]
    note: str | None = None


class Vocabulary:
    def __init__(self, signs: list[Sign]):
        self.signs = signs
        self.by_gloss = {sign.gloss: sign for sign in signs}
        self.by_form: dict[str, str] = {}
        for sign in signs:
            for form in sign.forms:
                self.by_form[slug(form)] = sign.gloss
        self.forms: list[str] = [form for sign in signs for form in sign.forms]
        self.gloss_of_form: list[str] = [sign.gloss for sign in signs for _ in sign.forms]

    @property
    def contexts(self) -> list[str]:
        seen: list[str] = []
        for sign in self.signs:
            for context in sign.contexts:
                if context not in seen:
                    seen.append(context)
        return seen

    @classmethod
    def load(cls, path: Path | None = None) -> "Vocabulary":
        data = json.loads(Path(path or vocabulary_path()).read_text(encoding="utf-8"))
        return cls(
            [
                Sign(s["gloss"], tuple(s["pt"]), tuple(s["contexts"]), s.get("note"))
                for s in data["signs"]
            ]
        )
