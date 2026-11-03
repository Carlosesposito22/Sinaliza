"""Grava o esquema OpenAPI do mock em docs/openapi-mock.json (para gerar tipos e clientes no front)."""
import json
from pathlib import Path

from .server import app

path = Path(__file__).resolve().parents[2] / "docs" / "openapi-mock.json"
path.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"gravado {path}")
