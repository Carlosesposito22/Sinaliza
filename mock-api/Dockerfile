# Contexto de build: a raiz do repositório (o mock lê data/vocabulary.json, data/phrases.json e data/trilha.json).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SINALIZA_VOCABULARY=/srv/data/vocabulary.json \
    SINALIZA_PHRASES=/srv/data/phrases.json \
    SINALIZA_TRILHA=/srv/data/trilha.json

WORKDIR /srv

COPY mock-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY mock-api/sinaliza_mock ./sinaliza_mock
COPY data/vocabulary.json data/phrases.json data/trilha.json ./data/

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "sinaliza_mock.server:app", "--host", "0.0.0.0", "--port", "8000"]
