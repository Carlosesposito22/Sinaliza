import csv
import json
from pathlib import Path

import numpy as np

from vlibrasil import (
    detection_rates,
    file_key,
    list_clips,
    load_vocabulary,
    output_path,
    parse_clip,
    process_folder,
    trim_rest,
)

LEFT_WRIST, RIGHT_WRIST = 15, 16


def write_vocabulary(path: Path) -> Path:
    signs = [
        {"gloss": "BANHEIRO", "video_class": "Banheiro", "pt": ["banheiro"], "contexts": ["serviços"]},
        {"gloss": "DOR DE CABEÇA", "video_class": "Dor de cabeça", "pt": ["dor de cabeça"], "contexts": ["saúde"]},
        {"gloss": "RÃ", "video_class": "Rã (sapo)", "pt": ["rã"], "contexts": ["geral"]},
        {"gloss": "SEM VÍDEO", "video_class": "Inexistente", "pt": ["x"], "contexts": ["geral"]},
        {"gloss": "SEM CLASSE", "pt": ["y"], "contexts": ["geral"]},
    ]
    path.write_text(json.dumps({"signs": signs}, ensure_ascii=False), encoding="utf-8")
    return path


def make_videos(root: Path) -> None:
    root.mkdir(parents=True)
    names = [
        "Banheiro_Articulador1.mp4", "Banheiro_Articulador2.mp4", "Banheiro_Articulador3.mp4",
        "Dor de cabeça_Articulador1.mp4", "Dor de cabeça_Articulador2.mp4",
        "Rã (sapo)_Articulador3.mp4",
        "Casa_Articulador1.mp4",
        "leiame.txt", "sem_articulador.mp4",
    ]
    for name in names:
        (root / name).write_bytes(b"video")


def motion_sequence(n_rest: int = 20, n_move: int = 30) -> np.ndarray:
    """Repouso, movimento do punho direito e repouso. Punhos em (frames, 75, 3)."""
    n = n_rest + n_move + n_rest
    kp = np.zeros((n, 75, 3), dtype=np.float32)
    kp[:, LEFT_WRIST] = [0.5, -1.2, 0.0]
    kp[:, RIGHT_WRIST] = [-0.5, -1.2, 0.0]
    t = np.linspace(0, 2 * np.pi, n_move)
    kp[n_rest : n_rest + n_move, RIGHT_WRIST, 0] = -0.5 + 0.4 * np.sin(t)
    kp[n_rest : n_rest + n_move, RIGHT_WRIST, 1] = -1.2 + 1.0 * (1 - np.cos(t)) / 2
    kp[n_rest + n_move :, RIGHT_WRIST] = kp[0, RIGHT_WRIST]
    return kp


def test_file_key_is_safe_and_accent_free():
    assert file_key("Dor de cabeça") == "DOR_DE_CABECA"
    assert file_key("Rã (sapo)") == "RA_SAPO"
    assert file_key("DOR_DE_CABECA") == "DOR_DE_CABECA"
    assert file_key("Cartão de Crédito") == "CARTAO_DE_CREDITO"


def test_parse_clip_extracts_label_and_signer():
    clip = parse_clip(Path("Dor de cabeça_Articulador2.mp4"))
    assert (clip.label, clip.signer) == ("Dor de cabeça", "02")
    assert parse_clip(Path("sem_articulador.mp4")) is None
    assert parse_clip(Path("Banheiro_Articulador1.txt")) is None


def test_list_clips_skips_other_files(tmp_path):
    root = tmp_path / "data"
    make_videos(root)
    clips = list_clips(root)
    assert len(clips) == 7
    assert {c.signer for c in clips} == {"01", "02", "03"}


def test_load_vocabulary_maps_only_signs_with_a_video_class(tmp_path):
    mapping = load_vocabulary(write_vocabulary(tmp_path / "v.json"))
    assert mapping == {
        "BANHEIRO": "BANHEIRO",
        "DOR_DE_CABECA": "DOR DE CABEÇA",
        "RA_SAPO": "RÃ",
        "INEXISTENTE": "SEM VÍDEO",
    }


def test_output_path_uses_signer_folder_and_safe_gloss(tmp_path):
    clip = parse_clip(Path("Dor de cabeça_Articulador2.mp4"))
    assert output_path(tmp_path, clip, "DOR DE CABEÇA") == tmp_path / "02" / "DOR_DE_CABECA_1.npy"


def test_trim_rest_keeps_the_motion_with_a_margin_and_drops_the_rest():
    kp = motion_sequence()
    trimmed = trim_rest(kp, pad=3)
    assert len(trimmed) < len(kp)
    assert 30 <= len(trimmed) <= 30 + 2 * 3 + 6
    # o movimento inteiro continua dentro do trecho mantido
    assert trimmed[:, RIGHT_WRIST, 1].max() > -0.3
    assert trimmed[0, RIGHT_WRIST, 1] == -1.2 or trimmed[0, RIGHT_WRIST, 1] < -1.1


def test_trim_rest_returns_the_whole_video_when_nothing_moves_or_it_is_too_short():
    still = np.zeros((60, 75, 3), dtype=np.float32)
    still[:, [LEFT_WRIST, RIGHT_WRIST]] = [0.3, -1.0, 0.0]
    assert len(trim_rest(still)) == 60
    assert len(trim_rest(still[:5])) == 5


def test_trim_rest_ignores_frames_where_the_wrist_is_missing():
    kp = motion_sequence()
    kp[10:15, RIGHT_WRIST] = 0.0  # pose perdida: zero não é movimento
    trimmed = trim_rest(kp, pad=3)
    assert len(trimmed) < len(kp)


def test_detection_rates_report_body_and_each_hand():
    kp = np.ones((4, 75, 3), dtype=np.float32)
    kp[2:, 54:] = 0
    assert detection_rates(kp) == (1.0, 1.0, 0.5)


def fake_extract(_path: Path) -> np.ndarray:
    kp = motion_sequence()
    kp[:, 33:54] = 1.0  # mão esquerda presente; direita ausente
    return kp


def test_process_folder_extracts_only_vocabulary_clips_and_writes_the_layout(tmp_path):
    root = tmp_path / "data"
    make_videos(root)
    out = tmp_path / "out"
    messages: list[str] = []

    counts = process_folder(root, out, write_vocabulary(tmp_path / "v.json"), extract_fn=fake_extract, log=messages.append)

    assert counts == {"processed": 6, "existing": 0, "outside_vocabulary": 1, "failed": 0}
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob("*.npy")) == [
        "01/BANHEIRO_1.npy",
        "01/DOR_DE_CABECA_1.npy",
        "02/BANHEIRO_1.npy",
        "02/DOR_DE_CABECA_1.npy",
        "03/BANHEIRO_1.npy",
        "03/RA_1.npy",
    ]
    assert any("SEM VÍDEO" in m for m in messages)  # sinal do vocabulário sem vídeo
    saved = np.load(out / "01" / "BANHEIRO_1.npy")
    assert saved.shape[1:] == (75, 3) and len(saved) < len(motion_sequence())
    with (out / "extraction_log.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert rows[0]["frames_raw"] == str(len(motion_sequence())) and int(rows[0]["frames_kept"]) < int(rows[0]["frames_raw"])
    assert rows[0]["right_hand_rate"] == "0.000" and rows[0]["left_hand_rate"] == "1.000"


def test_process_folder_is_resumable_respects_limit_and_can_skip_trimming(tmp_path):
    root = tmp_path / "data"
    make_videos(root)
    out = tmp_path / "out"
    vocabulary = write_vocabulary(tmp_path / "v.json")

    first = process_folder(root, out, vocabulary, limit=2, extract_fn=fake_extract, log=lambda _: None)
    assert first["processed"] == 2
    second = process_folder(root, out, vocabulary, extract_fn=fake_extract, trim=False, log=lambda _: None)
    assert second["processed"] == 4 and second["existing"] == 2
    assert not list(out.rglob("*.part"))
    untrimmed = [np.load(p) for p in out.rglob("*.npy") if len(np.load(p)) == len(motion_sequence())]
    assert len(untrimmed) == 4  # os 2 primeiros foram aparados, os 4 seguintes não


def test_process_folder_counts_failures_without_stopping(tmp_path):
    root = tmp_path / "data"
    make_videos(root)

    def flaky(path: Path) -> np.ndarray:
        if "Banheiro_Articulador2" in path.name:
            raise ValueError("vídeo corrompido")
        return fake_extract(path)

    counts = process_folder(
        root, tmp_path / "out", write_vocabulary(tmp_path / "v.json"), extract_fn=flaky, log=lambda _: None
    )
    assert counts["failed"] == 1 and counts["processed"] == 5
