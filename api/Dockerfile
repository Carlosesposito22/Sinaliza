# Contexto de build: a raiz do repositório (ver docker-compose.yml), porque a API
# lê data/vocabulary.json e data/phrases.json e usa o pacote textgloss (modelo T1 e gravação das inferências).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SINALIZA_VOCABULARY=/srv/data/vocabulary.json \
    SINALIZA_PHRASES=/srv/data/phrases.json

WORKDIR /srv

COPY api/requirements.txt api/requirements-ml.txt ./
RUN pip install --no-cache-dir -r requirements-ml.txt \
    && python -m spacy download pt_core_news_md

COPY api/app ./app
# Só o que a API usa do pacote de ML: config, atributos do spaCy, inferência e o esquema de `inferencias`.
COPY textgloss/__init__.py textgloss/config.py textgloss/features.py textgloss/infer.py textgloss/monitor.py ./textgloss/
COPY data/vocabulary.json data/phrases.json ./data/

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
