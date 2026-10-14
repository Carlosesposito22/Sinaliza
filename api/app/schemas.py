from pydantic import BaseModel, Field, field_validator


class PoseSequence(BaseModel):
    fps: int
    layout: dict[str, tuple[int, int]]
    frames: list[list[list[float]]]


class TranslateRequest(BaseModel):
    text: str = Field(max_length=500)

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("o texto não pode ser vazio")
        return value


class TranslateResponse(BaseModel):
    text: str
    glosses: list[str]
    pose: PoseSequence
