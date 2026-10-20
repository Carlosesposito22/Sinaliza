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


def fold(text: str) -> str:
    """Minúsculas, com acento (NFC). "avó" e "avô" continuam diferentes."""
    return unicodedata.normalize("NFC", text).casefold()


def vocabulary_path() -> Path:
    return Path(os.environ.get("SINALIZA_VOCABULARY", DEFAULT_PATH))


@dataclass(frozen=True)
class Sign:
    gloss: str
    forms: tuple[str, ...]
    contexts: tuple[str, ...]
    note: str | None = None
    video_class: str | None = None


class Vocabulary:
    def __init__(self, signs: list[Sign]):
        self.signs = signs
        self.by_gloss = {sign.gloss: sign for sign in signs}
        self._exact: dict[str, str] = {}
        self._unaccented: dict[str, set[str]] = {}
        for sign in signs:
            for form in sign.forms:
                self._exact[fold(form)] = sign.gloss
                self._unaccented.setdefault(slug(form), set()).add(sign.gloss)
        self.forms: list[str] = [form for sign in signs for form in sign.forms]
        self.gloss_of_form: list[str] = [sign.gloss for sign in signs for _ in sign.forms]
        self.max_words = max((len(form.split()) for form in self.forms), default=1)

    def lookup(self, text: str) -> str | None:
        """Glosa da forma `text`: primeiro com acento; sem acento só se for uma única glosa."""
        gloss = self._exact.get(fold(text))
        if gloss is not None:
            return gloss
        candidates = self._unaccented.get(slug(text), set())
        if len(candidates) == 1:
            return next(iter(candidates))
        return None

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
                Sign(s["gloss"], tuple(s["pt"]), tuple(s["contexts"]), s.get("note"), s.get("video_class"))
                for s in data["signs"]
            ]
        )
