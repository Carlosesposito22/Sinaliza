"""Caminhos e parâmetros compartilhados pela ingestão, pela preparação e pelos DAGs."""
import os
from pathlib import Path

ROOT = Path(os.environ.get("SINALIZA_ROOT", Path(__file__).resolve().parents[1]))
RAW_DIR = ROOT / "data" / "raw" / "vlibrasbd"
PROCESSED_DIR = ROOT / "data" / "processed" / "vlibrasbd"

CSV_NAME = "pt_br2libras_gloss.csv"
# Valores publicados pelo Mendeley Data (DOI 10.17632/ryj88ckjww.2).
CSV_URL = (
    "https://data.mendeley.com/public-files/datasets/ryj88ckjww/files/"
    "69d3709a-e238-406b-9aba-04fe15410a01/file_downloaded"
)
CSV_SHA256 = "de0f1ddf8368b7f343b07c00e5f122ac46193d1aea2c36b642e0805c5c73fcbf"

DATABASE_URL = os.environ.get(
    "SINALIZA_DATABASE_URL",
    "postgresql+psycopg://sinaliza:sinaliza@localhost:5432/sinaliza",
)

SPACY_MODEL = "pt_core_news_md"
SEED = 42
TEST_FRACTION = 0.10
