import json
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest
from sqlalchemy import create_engine, insert

import data
from receptor.receptor import ensure_schema, mensagens_mqtt, totens

NOW = datetime.now(timezone.utc).replace(microsecond=0)


def msg(i, device="totem-ubs", seq=None, status="inferida", latency=350.0, minutes_ago=5):
    return dict(msg_id=f"m-{device}-{i}", dispositivo=device, local="UBS", topico=f"sinaliza/totens/{device}/frases",
                seq=seq if seq is not None else i, enviada_em=NOW - timedelta(minutes=minutes_ago),
                recebida_em=NOW - timedelta(minutes=minutes_ago), texto=f"frase {i}", status=status,
                glosas=json.dumps(["BOM-DIA"]) if status == "inferida" else None, versao_modelo="sinaliza-t1/1",
                latencia_api_ms=40.0, latencia_total_ms=latency if status == "inferida" else None, tentativas=1)


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    ensure_schema(engine)
    return engine


def test_empty_when_the_tables_do_not_exist():
    engine = create_engine("sqlite://")
    assert data.load_mqtt(engine).empty and data.load_devices(engine).empty
    assert data.mqtt_summary(data.load_mqtt(engine))["mensagens"] == 0


def test_lost_messages_counts_gaps_and_handles_restarts():
    assert data.lost_messages(pd.Series([1, 2, 3])) == 0
    assert data.lost_messages(pd.Series([1, 2, 5])) == 2
    assert data.lost_messages(pd.Series([3, 4, 1, 2, 4])) == 1  # reiniciou no 1; faltou o 3 do segundo trecho
    assert data.lost_messages(pd.Series([], dtype=float)) == 0


def test_summary_devices_and_recent_table(engine):
    rows = [msg(1), msg(2, latency=100.0), msg(4, latency=900.0), msg(5, status="rejeitada"),
            msg(1, device="totem-inss"), msg(2, device="totem-inss", status="erro")]
    with engine.begin() as conn:
        conn.execute(insert(mensagens_mqtt), rows)
        conn.execute(insert(totens), [dict(dispositivo="totem-ubs", status="online", local="UBS", atualizado_em=NOW),
                                      dict(dispositivo="totem-inss", status="offline", local="INSS", atualizado_em=NOW)])
    msgs, devices = data.load_mqtt(engine), data.load_devices(engine)
    summary = data.mqtt_summary(msgs)
    assert (summary["mensagens"], summary["inferidas"], summary["rejeitadas"], summary["erros"]) == (6, 4, 1, 1)
    assert summary["perdidas"] == 1  # o 3 do totem-ubs
    assert summary["latencia_p50_ms"] == pytest.approx(350.0)

    table = data.devices_table(msgs, devices).set_index("totem")
    assert table.loc["totem-ubs", "estado"] == "online" and table.loc["totem-ubs", "perdidas"] == 1
    assert table.loc["totem-inss", "estado"] == "offline" and table.loc["totem-inss", "mensagens"] == 2

    recent = data.mqtt_recent_table(msgs)
    assert list(recent.columns)[:3] == ["recebida (UTC)", "totem", "seq"]
    assert "BOM-DIA" in recent["sequência de sinais"].tolist() and "—" in recent["sequência de sinais"].tolist()


def test_per_interval_fills_empty_bins(engine):
    with engine.begin() as conn:
        conn.execute(insert(mensagens_mqtt), [msg(1, minutes_ago=50), msg(2, minutes_ago=5)])
    per = data.mqtt_per_interval(data.load_mqtt(engine), NOW - timedelta(hours=1))
    assert per["mensagens"].sum() == 2 and (per["mensagens"] == 0).any()


def test_broker_check(monkeypatch):
    assert data.check_broker("", 1883).ok is None
    assert data.check_broker("127.0.0.1", 1).ok is False
