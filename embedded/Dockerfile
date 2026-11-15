# Totem de atendimento simulado (sistema embarcado). Contexto de build: a raiz do repositório.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY embedded/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY embedded/totem.py ./embedded/totem.py
# Frases públicas de atendimento (as mesmas do simulador de uso).
COPY data/phrases.json ./data/phrases.json
CMD ["python", "embedded/totem.py"]
