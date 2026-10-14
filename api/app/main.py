from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .generator import PoseGenerator, StubGenerator
from .schemas import TranslateRequest, TranslateResponse

app = FastAPI(title="Sinaliza API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

generator: PoseGenerator = StubGenerator()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest) -> TranslateResponse:
    glosses = generator.to_glosses(request.text)
    if not glosses:
        raise HTTPException(status_code=422, detail="o texto não contém palavras")
    return TranslateResponse(
        text=request.text,
        glosses=glosses,
        pose=generator.generate(glosses),
    )
