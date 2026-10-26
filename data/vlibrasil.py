"""Processamento em lote do V-LIBRASIL (pasta de .mp4) para keypoints.

Estrutura do dataset (como o Carlos o baixou):

    <pasta>/data/<Sinal>_Articulador<N>.mp4       N = 1, 2, 3 (os três sinalizantes)
    <pasta>/annotations.csv                       video_id, video_name, class, user_id, ...

Só os sinais do `vocabulary.json` (campo `video_class`) são extraídos. Saída:

    <saída>/<NN>/<GLOSA>_1.npy        NN = 01..03; GLOSA sem acento, `_` entre palavras

é o layout lido por `model/sinaliza_model/data.py` (uma gravação por sinalizante).

Cada gravação tem repouso no começo e no fim (a pessoa sobe e baixa os braços); `trim_rest`
apara esses trechos pela velocidade dos punhos antes de salvar.

Os vídeos do V-LIBRASIL só podem ser usados para pesquisa e ensino e **não podem ser
redistribuídos**: não versione a saída (`*.npy` já está no .gitignore).
"""

import csv
import json
import re
import unicodedata
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import numpy as np

POSE_COUNT = 33
HAND_COUNT = 21
LEFT_WRIST, RIGHT_WRIST = 15, 16

CLIP_PATTERN = re.compile(r"^(?P<label>.+)_Articulador(?P<signer>\d+)$")
LOG_COLUMNS = [
    "signer", "gloss", "video_class", "frames_raw", "frames_kept",
    "pose_rate", "left_hand_rate", "right_hand_rate", "source",
]


def slug(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper()


def file_key(text: str) -> str:
    """Nome de arquivo seguro: sem acento, maiúsculas, não alfanumérico vira `_`."""
    return re.sub(r"[^A-Z0-9]+", "_", slug(text)).strip("_")


@dataclass(frozen=True)
class Clip:
    path: Path
    label: str
    signer: str


def parse_clip(path: Path) -> Clip | None:
    match = CLIP_PATTERN.match(unicodedata.normalize("NFC", path.stem))
    if not match or path.suffix.lower() != ".mp4":
        return None
    return Clip(path, match["label"], f"{int(match['signer']):02d}")


def list_clips(root: Path) -> list[Clip]:
    clips = [c for p in sorted(Path(root).glob("*.mp4")) if (c := parse_clip(p))]
    return sorted(clips, key=lambda c: (file_key(c.label), c.signer))


def load_vocabulary(path: Path) -> dict[str, str]:
    """`file_key(video_class)` → glosa, para os sinais que têm `video_class`."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for sign in data["signs"]:
        if sign.get("video_class"):
            mapping[file_key(sign["video_class"])] = sign["gloss"]
    return mapping


def output_path(out_root: Path, clip: Clip, gloss: str) -> Path:
    return Path(out_root) / clip.signer / f"{file_key(gloss)}_1.npy"


def trim_rest(
    keypoints: np.ndarray,
    pad: int = 3,
    ratio: float = 0.25,
    floor: float = 0.004,
    window: int = 5,
) -> np.ndarray:
    """Apara o repouso do começo e do fim pela velocidade dos punhos (pose 15 e 16).

    O limiar é uma fração (`ratio`) do 90º percentil da velocidade do próprio vídeo, com piso
    `floor` (em larguras de ombro por quadro) para não tratar ruído como movimento. Mantém
    `pad` quadros de folga. Se não achar movimento, devolve o vídeo inteiro.
    """
    n = len(keypoints)
    if n < 2 * pad + 4:
        return keypoints
    wrists = keypoints[:, [LEFT_WRIST, RIGHT_WRIST], :2]
    present = np.abs(wrists).sum(axis=2) > 0
    step = np.linalg.norm(np.diff(wrists, axis=0), axis=2)
    speed = np.where(present[1:] & present[:-1], step, 0.0).max(axis=1)
    if window > 1 and len(speed) >= window:
        speed = np.convolve(speed, np.ones(window) / window, mode="same")
    threshold = max(ratio * float(np.percentile(speed, 90)), floor)
    active = np.flatnonzero(speed > threshold)
    if len(active) < 3:
        return keypoints
    first = max(0, int(active[0]) - pad)
    last = min(n, int(active[-1]) + 2 + pad)
    return keypoints[first:last]


def detection_rates(keypoints: np.ndarray) -> tuple[float, float, float]:
    """Fração de quadros com corpo, mão esquerda e mão direita detectados."""
    present = np.abs(keypoints).sum(axis=2) > 0
    pose = present[:, :POSE_COUNT].any(axis=1).mean()
    left = present[:, POSE_COUNT : POSE_COUNT + HAND_COUNT].any(axis=1).mean()
    right = present[:, POSE_COUNT + HAND_COUNT :].any(axis=1).mean()
    return float(pose), float(left), float(right)


_DETECTOR = None


def _extract_job(job: tuple[str, dict]) -> tuple[str, np.ndarray | None, str]:
    """Tarefa de um processo: extrai um vídeo. Devolve (caminho, keypoints, erro)."""
    global _DETECTOR
    path, options = job
    try:
        from extract_keypoints import extract

        detector = None
        if options.get("yolo"):
            if _DETECTOR is None:
                from person_crop import YoloPersonDetector

                _DETECTOR = YoloPersonDetector(
                    options["yolo_model"], options["yolo_confidence"], options["yolo_device"]
                )
            detector = _DETECTOR
        keypoints = extract(
            Path(path),
            options["max_width"],
            detector,
            options["crop_margin"],
            options["crop_every"],
            options["upper_body"],
            options["target_fps"],
            Path(options["hand_model"]) if options.get("hand_model") else None,
        )
        return path, keypoints, ""
    except Exception as error:  # noqa: BLE001 - um vídeo ruim não pode derrubar o lote
        return path, None, f"{type(error).__name__}: {error}"


def process_folder(
    root: Path,
    out_root: Path,
    vocabulary_path: Path,
    workers: int = 1,
    limit: int | None = None,
    trim: bool = True,
    options: dict | None = None,
    extract_fn: Callable[[Path], np.ndarray] | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, int]:
    """Extrai os vídeos do vocabulário. Retomável: pula `.npy` que já existem.

    Com `extract_fn` roda em série (testes); sem ele, usa `workers` processos.
    """
    vocabulary = load_vocabulary(vocabulary_path)
    all_clips = list_clips(root)
    counts = {"processed": 0, "existing": 0, "outside_vocabulary": 0, "failed": 0}

    selected: list[tuple[Clip, str]] = []
    for clip in all_clips:
        gloss = vocabulary.get(file_key(clip.label))
        if gloss is None:
            counts["outside_vocabulary"] += 1
        else:
            selected.append((clip, gloss))

    found = {file_key(clip.label) for clip, _ in selected}
    for key, gloss in vocabulary.items():
        if key not in found:
            log(f"aviso: nenhum vídeo para {gloss} ({key})")

    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    pending: list[tuple[Clip, str, Path]] = []
    for clip, gloss in selected:
        target = output_path(out_root, clip, gloss)
        if target.exists():
            counts["existing"] += 1
        else:
            pending.append((clip, gloss, target))
    if limit is not None:
        pending = pending[:limit]

    log_path = out_root / "extraction_log.csv"
    new_log = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as log_file:
        writer = csv.writer(log_file)
        if new_log:
            writer.writerow(LOG_COLUMNS)

        def save(clip: Clip, gloss: str, target: Path, keypoints: np.ndarray) -> None:
            kept = trim_rest(keypoints) if trim else keypoints
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + ".part")
            with partial.open("wb") as handle:
                np.save(handle, kept.astype(np.float32))
            partial.replace(target)
            pose, left, right = detection_rates(kept)
            writer.writerow(
                [clip.signer, file_key(gloss), clip.label, len(keypoints), len(kept),
                 f"{pose:.3f}", f"{left:.3f}", f"{right:.3f}", clip.path.name]
            )
            log_file.flush()
            counts["processed"] += 1
            log(f"{clip.signer}/{target.name}: {len(keypoints)}→{len(kept)} frames "
                f"(corpo {pose:.0%}, mão esq. {left:.0%}, mão dir. {right:.0%})")

        if extract_fn is not None or workers <= 1:
            run = extract_fn or (lambda path: _serial_extract(path, options or {}))
            for clip, gloss, target in pending:
                try:
                    keypoints = run(clip.path)
                except Exception as error:  # noqa: BLE001
                    counts["failed"] += 1
                    log(f"falhou {clip.path.name}: {type(error).__name__}: {error}")
                    continue
                save(clip, gloss, target, keypoints)
        else:
            by_path = {str(clip.path): (clip, gloss, target) for clip, gloss, target in pending}
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_extract_job, (path, options or {})) for path in by_path]
                for future in as_completed(futures):
                    path, keypoints, error = future.result()
                    clip, gloss, target = by_path[path]
                    if keypoints is None:
                        counts["failed"] += 1
                        log(f"falhou {clip.path.name}: {error}")
                        continue
                    save(clip, gloss, target, keypoints)
    return counts


def _serial_extract(path: Path, options: dict) -> np.ndarray:
    _, keypoints, error = _extract_job((str(path), options))
    if keypoints is None:
        raise RuntimeError(error)
    return keypoints

