from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, insert, select

from textgloss import monitor


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    monitor.ensure_schema(engine)
    return engine


def frase(em, versao="1", palavras=10, mantidas=6, sem_sinal=1, incertas=2, prob=0.8, latencia=20.0, usou=True):
    return dict(em=em, texto="x", n_palavras=palavras, n_mantidas=mantidas, n_sem_sinal=sem_sinal,
                prob_incerta=incertas, prob_media=prob, latencia_ms=latencia, versao_modelo=versao,
                usou_modelo=usou, palavras="[]", processada=False)


def hora(h, minuto=0):
    return datetime(2026, 11, 5, h, minuto, tzinfo=timezone.utc)


def test_sem_frases_novas_nao_faz_nada(engine):
    assert monitor.process(engine) == {"frases_novas": 0, "horas_atualizadas": 0}


def test_agrega_por_hora_e_versao(engine):
    with engine.begin() as conn:
        conn.execute(insert(monitor.inferencias), [
            frase(hora(9, 5)), frase(hora(9, 40), latencia=40.0),
            frase(hora(10, 1)), frase(hora(9, 10), versao="2"),
        ])
    assert monitor.process(engine) == {"frases_novas": 4, "horas_atualizadas": 3}
    with engine.connect() as conn:
        rows = {(r.hora.hour, r.versao_modelo): r for r in conn.execute(select(monitor.indicadores_horarios))}
    nove = rows[(9, "1")]
    assert nove.frases == 2 and nove.palavras == 20
    assert nove.taxa_manter == pytest.approx(0.6)
    assert nove.taxa_sem_sinal == pytest.approx(0.1)
    assert nove.latencia_p50_ms == pytest.approx(30.0)
    assert nove.sem_modelo == 0


def test_marca_processadas_e_nao_conta_duas_vezes(engine):
    with engine.begin() as conn:
        conn.execute(insert(monitor.inferencias), [frase(hora(9))])
    monitor.process(engine)
    assert monitor.process(engine)["frases_novas"] == 0
    with engine.connect() as conn:
        assert conn.execute(select(monitor.indicadores_horarios.c.frases)).scalar_one() == 1


def test_frases_tardias_da_mesma_hora_somam(engine):
    with engine.begin() as conn:
        conn.execute(insert(monitor.inferencias), [frase(hora(9), mantidas=10, sem_sinal=0)])
    monitor.process(engine)
    with engine.begin() as conn:
        conn.execute(insert(monitor.inferencias), [frase(hora(9, 50), mantidas=0, sem_sinal=10)])
    monitor.process(engine)
    with engine.connect() as conn:
        row = conn.execute(select(monitor.indicadores_horarios)).one()
    assert row.frases == 2 and row.palavras == 20
    assert row.taxa_manter == pytest.approx(0.5)
    assert row.taxa_sem_sinal == pytest.approx(0.5)


def test_conta_frases_sem_modelo(engine):
    with engine.begin() as conn:
        conn.execute(insert(monitor.inferencias), [frase(hora(9), versao="lista-fixa", usou=False), frase(hora(9))])
    monitor.process(engine)
    with engine.connect() as conn:
        rows = {r.versao_modelo: r.sem_modelo for r in conn.execute(select(monitor.indicadores_horarios))}
    assert rows == {"lista-fixa": 1, "1": 0}


def test_purge_apaga_texto_so_de_processadas_antigas(engine):
    velho = datetime.now(timezone.utc) - timedelta(days=40)
    novo = datetime.now(timezone.utc) - timedelta(days=1)
    with engine.begin() as conn:
        conn.execute(insert(monitor.inferencias), [
            {**frase(velho), "texto": "antiga processada", "processada": True},
            {**frase(velho), "texto": "antiga pendente", "processada": False},
            {**frase(novo), "texto": "recente processada", "processada": True},
        ])
    assert monitor.purge(engine, 30) == 1
    with engine.connect() as conn:
        textos = sorted(r.texto or "" for r in conn.execute(select(monitor.inferencias.c.texto)))
    assert textos == ["", "antiga pendente", "recente processada"]
    assert monitor.purge(engine, 30) == 0
