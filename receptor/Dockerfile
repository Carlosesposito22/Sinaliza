# Receptor MQTT: grava as frases dos totens e pede a inferência à API. Contexto de build: a raiz do repositório.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY receptor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY receptor/receptor.py .
CMD ["python", "receptor.py"]
