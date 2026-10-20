import csv
import unicodedata
import zipfile
from pathlib import Path

import numpy as np

from minds_libras import detection_rates, parse_member, process_zip

VOCABULARY = Path(__file__).resolve().parents[1] / "vocabulary-minds.json"


def fake_extract(_path: Path) -> np.ndarray:
    frames = np.ones((6, 75, 3), dtype=np.float32)
    frames[3:, 54:] = 0  # mão direita some nos últimos frames
    return frames


def build_zip(path: Path) -> None:
    maca = unicodedata.normalize("NFD", "13MaçãSinalizador01-2.mp4")
    names = [
        "Sinalizador01/",
        "Sinalizador01/.DS_Store",
        "__MACOSX/Sinalizador01/Canon/._01AcontecerSinalizador01-1.mp4",
        "Sinalizador01/Canon/01AcontecerSinalizador01-1.mp4",
        "Sinalizador01/Canon/01AcontecerSinalizador01-2.mp4",
        f"Sinalizador01/Canon/{maca}",
        "Sinalizador01/Canon/99InexistenteSinalizador01-1.mp4",
        "Sinalizador01/Kinect/01AcontecerSinalizador01-3.mp4",
        "Sinalizador01/Canon/leiame.txt",
    ]
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, b"" if name.endswith("/") else b"video")


def test_parse_member_extracts_fields():
    member = parse_member("Sinalizador07/Canon/20VontadeSinalizador07-5.mp4")
    assert (member.sign, member.signer, member.rep) == ("Vontade", "07", 5)


def test_parse_member_ignores_macos_hidden_and_other_cameras():
    assert parse_member("__MACOSX/Sinalizador01/Canon/._01AcontecerSinalizador01-1.mp4") is None
    assert parse_member("Sinalizador01/Canon/.DS_Store") is None
    assert parse_member("Sinalizador01/Kinect/01AcontecerSinalizador01-1.mp4") is None
    assert parse_member("Sinalizador01/Kinect/01AcontecerSinalizador01-1.mp4", camera=None)


def test_detection_rates():
    pose, left, right = detection_rates(fake_extract(Path()))
    assert (pose, left, right) == (1.0, 1.0, 0.5)


def test_process_zip_writes_expected_layout(tmp_path):
    archive = tmp_path / "Sinalizador01.zip"
    build_zip(archive)
    out = tmp_path / "out"

    counts = process_zip(archive, out, VOCABULARY, fake_extract, log=lambda _: None)

    assert counts == {"processed": 3, "existing": 0, "unknown_sign": 1, "ignored": 2}
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob("*.npy")) == [
        "01/ACONTECER_1.npy",
        "01/ACONTECER_2.npy",
        "01/MACA_2.npy",
    ]
    assert np.load(out / "01" / "MACA_2.npy").shape == (6, 75, 3)
    with (out / "extraction_log.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 3
    assert rows[0]["right_hand_rate"] == "0.500"


def test_process_zip_is_resumable_and_respects_limit(tmp_path):
    archive = tmp_path / "Sinalizador01.zip"
    build_zip(archive)
    out = tmp_path / "out"

    first = process_zip(archive, out, VOCABULARY, fake_extract, limit=1, log=lambda _: None)
    assert first["processed"] == 1

    second = process_zip(archive, out, VOCABULARY, fake_extract, log=lambda _: None)
    assert second["processed"] == 2
    assert second["existing"] == 1
    assert not list(out.rglob("*.part"))
