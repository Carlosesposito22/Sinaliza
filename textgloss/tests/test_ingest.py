import hashlib
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from textgloss import config, ingest

CSV = "pt-br,libras-gloss,is_government_source,english_translation\nOlá,OLÁ,False,Hello\n".encode("utf-8")
ERRO = b'{"url":"x","error":"invalid json response body ... Unexpected token"}'  # o que o Mendeley já devolveu com status 200

RESPOSTAS: list = []
PEDIDOS: list = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        PEDIDOS.append(self.headers.get("User-Agent"))
        corpo = RESPOSTAS.pop(0) if RESPOSTAS else CSV
        self.send_response(200)
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass


@pytest.fixture
def mendeley(monkeypatch):
    RESPOSTAS.clear()
    PEDIDOS.clear()
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "CSV_URL", f"http://127.0.0.1:{httpd.server_port}/csv")
    monkeypatch.setattr(config, "CSV_SHA256", hashlib.sha256(CSV).hexdigest())
    yield
    httpd.shutdown()


def test_downloads_and_confirms_the_hash(mendeley, tmp_path):
    destino = tmp_path / "corpus.csv"
    assert ingest.download(destino, wait=0) == destino
    assert destino.read_bytes() == CSV and not (tmp_path / "corpus.csv.part").exists()
    assert PEDIDOS[0].startswith("Mozilla/5.0")  # o Mendeley recusa o User-Agent padrão do urllib


def test_a_bad_answer_is_discarded_and_the_next_attempt_downloads_again(mendeley, tmp_path):
    RESPOSTAS.extend([ERRO, ERRO])  # as duas primeiras respostas são o erro em JSON; a terceira é o CSV
    destino = tmp_path / "corpus.csv"
    ingest.download(destino, wait=0)
    assert destino.read_bytes() == CSV and len(PEDIDOS) == 3


def test_gives_up_after_the_attempts_and_leaves_no_file_behind(mendeley, tmp_path):
    RESPOSTAS.extend([ERRO] * 4)
    destino = tmp_path / "corpus.csv"
    with pytest.raises(ValueError, match="4 tentativas") as error:
        ingest.download(destino, attempts=4, wait=0)
    assert "invalid json" in str(error.value)  # a mensagem mostra o que o servidor respondeu
    assert not destino.exists() and not (tmp_path / "corpus.csv.part").exists()


def test_an_existing_file_with_the_right_hash_is_not_downloaded_again(mendeley, tmp_path):
    destino = tmp_path / "corpus.csv"
    destino.write_bytes(CSV)
    ingest.download(destino, wait=0)
    assert PEDIDOS == []


def test_an_existing_file_with_a_different_hash_fails_and_is_not_deleted(mendeley, tmp_path):
    destino = tmp_path / "corpus.csv"
    destino.write_bytes(b"outra versao")
    with pytest.raises(ValueError, match="Hash do corpus diverge"):
        ingest.download(destino, wait=0)
    assert destino.read_bytes() == b"outra versao" and PEDIDOS == []
