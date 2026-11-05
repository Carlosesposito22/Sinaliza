"""Grava cada frase atendida em `inferencias` (Postgres), para o DAG `monitoramento` e o painel.

Falha de gravação NUNCA afeta a resposta da API: só vai para o log.

PRIVACIDADE: o texto digitado pode ter dado pessoal. As palavras e o texto só são gravados para o
`simulador` (frases públicas) ou com `SINALIZA_LOG_TEXT=true`; sem isso, ficam só a decisão, a
probabilidade e o tipo de cada palavra. O `monitoramento` apaga o texto depois da retenção.
"""
import json
import logging
import re
from collections.abc import Sequence

logger = logging.getLogger("sinaliza.log")

UNCERTAIN_RANGE = (0.4, 0.6)
ORIGIN_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")


def clean_origin(value: str | None) -> str:
    value = (value or "").strip().lower()
    return value if ORIGIN_PATTERN.match(value) else "desconhecida"


class InferenceLog:
    def __init__(self, database_url: str | None, log_text: bool = False):
        self.log_text = log_text
        self._engine = None
        self._monitor = None
        if not database_url:
            return
        try:
            from sqlalchemy import create_engine

            from textgloss import monitor
        except ImportError as error:
            logger.warning("gravação de inferências desligada (%s)", error)
            return
        self._engine = create_engine(database_url, pool_pre_ping=True)
        self._monitor = monitor
        self._schema_ready = False

    @property
    def enabled(self) -> bool:
        return self._engine is not None

    def record(self, *, text: str, matches: Sequence, model_version: str, used_model: bool,
               latency_ms: float, origin: str) -> None:
        if not self.enabled:
            return
        try:
            keep_text = self.log_text or origin == "simulador"
            words = sum(m.n_words for m in matches)
            kept = sum(m.n_words for m in matches if m.decision == "MANTER")
            without_sign = sum(m.n_words for m in matches if m.kind == "ignored")
            mean = sum(m.probability * m.n_words for m in matches) / max(words, 1)
            uncertain = sum(m.n_words for m in matches if UNCERTAIN_RANGE[0] <= m.probability <= UNCERTAIN_RANGE[1])
            detail = [
                {
                    **({"palavra": m.word, "glosa": m.gloss} if keep_text else {}),
                    "decisao": m.decision,
                    "probabilidade": round(m.probability, 4),
                    "tipo": m.kind,
                }
                for m in matches
            ]
            if not self._schema_ready:
                self._monitor.ensure_schema(self._engine)
                self._schema_ready = True
            with self._engine.begin() as conn:
                conn.execute(
                    self._monitor.inferencias.insert().values(
                        origem=origin,
                        texto=text if keep_text else None,
                        n_palavras=words,
                        n_mantidas=kept,
                        n_sem_sinal=without_sign,
                        prob_media=mean,
                        prob_incerta=uncertain,
                        latencia_ms=latency_ms,
                        versao_modelo=model_version,
                        usou_modelo=used_model,
                        palavras=json.dumps(detail, ensure_ascii=False),
                    )
                )
        except Exception as error:
            logger.warning("não foi possível gravar a inferência: %s", error)
