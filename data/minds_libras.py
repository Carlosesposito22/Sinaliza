"""Processamento em lote dos ZIPs do MINDS-Libras.

Estrutura observada nos ZIPs (cabeçalhos dos arquivos baixados):

    SinalizadorNN/Canon/<II><Sinal>SinalizadorNN-<repetição>.mp4

onde `II` é o índice do sinal (01–20). Os ZIPs trazem também `__MACOSX/` e
`.DS_Store`, ignorados aqui.

Saída (convenção lida por `model/sinaliza_model/data.py`):

    <saída>/<NN>/<SINAL>_<repetição>.npy      SINAL sem acento e em maiúsculas
"""

import csv
import json
import re
import shutil
import tempfile
import unicodedata
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import numpy as np

POSE_COUNT = 33
HAND_COUNT = 21

MEMBER_PATTERN = re.compile(
    r"^\d{2}(?P<sign>.+?)Sinalizador(?P<signer>\d{2})-(?P<rep>\d+)\.mp4$", re.IGNORECASE
)
LOG_COLUMNS = ["signer", "sign", "rep", "frames", "pose_rate", "left_hand_rate", "right_hand_rate", "source"]


@dataclass(frozen=True)
class Member:
    path: str
    sign: str
    signer: str
    rep: int


def slug(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).upper()


def load_sign_slugs(vocabulary_path: Path) -> set[str]:
    data = json.loads(Path(vocabulary_path).read_text(encoding="utf-8"))
    return {slug(sign["gloss"]) for sign in data["signs"]}


def parse_member(path: str, camera: str | None = "Canon") -> Member | None:
    """Devolve o membro do ZIP se for um vídeo de sinal; `None` caso contrário."""
    parts = PurePosixPath(path).parts
    if not parts or "__MACOSX" in parts:
        return None
    filename = unicodedata.normalize("NFC", parts[-1])
    if filename.startswith("."):
        return None
    if camera and camera not in parts[:-1]:
        return None
    match = MEMBER_PATTERN.match(filename)
    if not match:
        return None
    return Member(path, match["sign"], match["signer"], int(match["rep"]))


def output_path(out_root: Path, member: Member) -> Path:
    return out_root / member.signer / f"{slug(member.sign)}_{member.rep}.npy"


def detection_rates(keypoints: np.ndarray) -> tuple[float, float, float]:
    """Fração de frames com corpo, mão esquerda e mão direita detectados."""
    present = np.abs(keypoints).sum(axis=2) > 0
    pose = present[:, :POSE_COUNT].any(axis=1).mean()
    left = present[:, POSE_COUNT : POSE_COUNT + HAND_COUNT].any(axis=1).mean()
    right = present[:, POSE_COUNT + HAND_COUNT :].any(axis=1).mean()
    return float(pose), float(left), float(right)


def process_zip(
    zip_path: Path,
    out_root: Path,
    vocabulary_path: Path,
    extract_fn: Callable[[Path], np.ndarray],
    camera: str | None = "Canon",
    limit: int | None = None,
    log: Callable[[str], None] = print,
) -> dict[str, int]:
    """Extrai keypoints de cada vídeo do ZIP. Retomável: pula `.npy` já gerados."""
    known = load_sign_slugs(vocabulary_path)
    counts = {"processed": 0, "existing": 0, "unknown_sign": 0, "ignored": 0}
    out_root.mkdir(parents=True, exist_ok=True)
    log_path = out_root / "extraction_log.csv"
    new_log = not log_path.exists()

    with zipfile.ZipFile(zip_path) as archive, log_path.open("a", newline="", encoding="utf-8") as log_file:
        writer = csv.writer(log_file)
        if new_log:
            writer.writerow(LOG_COLUMNS)

        members: list[Member] = []
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = parse_member(info.filename, camera)
            if member is None:
                if info.filename.lower().endswith(".mp4"):
                    counts["ignored"] += 1
                continue
            if slug(member.sign) not in known:
                counts["unknown_sign"] += 1
                continue
            members.append(member)
        members.sort(key=lambda m: (m.signer, slug(m.sign), m.rep))

        for member in members:
            target = output_path(out_root, member)
            if target.exists():
                counts["existing"] += 1
                continue
            if limit is not None and counts["processed"] >= limit:
                break

            with tempfile.TemporaryDirectory() as tmp:
                video = Path(tmp) / "video.mp4"
                with archive.open(member.path) as source, video.open("wb") as destination:
                    shutil.copyfileobj(source, destination, 1 << 20)
                keypoints = extract_fn(video)

            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + ".part")
            with partial.open("wb") as handle:
                np.save(handle, keypoints.astype(np.float32))
            partial.replace(target)

            pose, left, right = detection_rates(keypoints)
            writer.writerow(
                [member.signer, slug(member.sign), member.rep, len(keypoints),
                 f"{pose:.3f}", f"{left:.3f}", f"{right:.3f}", Path(zip_path).name]
            )
            log_file.flush()
            counts["processed"] += 1
            log(f"{target.relative_to(out_root)}: {len(keypoints)} frames "
                f"(corpo {pose:.0%}, mão esq. {left:.0%}, mão dir. {right:.0%})")

    return counts
