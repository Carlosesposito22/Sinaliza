import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from textgloss import simulador

SEEN = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append((self.headers["X-Origem"], body["text"]))
        if "recusa" in body["text"]:
            self.send_response(422)
            payload = {"detail": "sem sinais"}
        else:
            self.send_response(200)
            payload = {"model_version": "sinaliza-t1/1", "latency_ms": 12, "glosses": ["MÃE"]}
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(payload).encode())

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    SEEN.clear()
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_run_sends_phrases_with_the_simulator_origin_and_counts_results(server):
    lines = []
    stats = simulador.run(server, ["a mãe chegou", "frase de recusa"], n=6, interval=0, seed=1, out=lines.append)
    assert stats["enviadas"] == 6 and stats["ok"] + stats["rejeitadas"] == 6 and stats["erros"] == 0
    assert stats["modelos"] == {"sinaliza-t1/1": stats["ok"]}
    assert {origin for origin, _ in SEEN} == {"simulador"}
    assert len(lines) == 6


def test_run_counts_network_errors_without_stopping():
    stats = simulador.run("http://127.0.0.1:9", ["a"], n=2, interval=0, seed=1, out=lambda _: None)
    assert stats["erros"] == 2 and stats["ok"] == 0


def test_the_public_phrases_file_loads():
    phrases = simulador.load_phrases("frases")
    assert len(phrases) >= 20 and all(isinstance(p, str) and p for p in phrases)
