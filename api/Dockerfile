# Contexto de build: a raiz do repositório (ver docker-compose.yml), porque a API
# lê data/vocabulary.json e data/phrases.json.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SINALIZA_VOCABULARY=/srv/data/vocabulary.json \
    SINALIZA_PHRASES=/srv/data/phrases.json

WORKDIR /srv

COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/app ./app
COPY data/vocabulary.json data/phrases.json ./data/

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
