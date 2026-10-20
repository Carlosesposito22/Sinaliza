"""Extrai keypoints (pose + mãos) de vídeos com YOLOv8 + MediaPipe Holistic.

O YOLOv8 localiza a pessoa e o vídeo é recortado em volta dela (recorte fixo por
vídeo); o MediaPipe roda no recorte, com mais pixels nas mãos. Os keypoints são
convertidos para pixels do quadro original antes de normalizar, então o recorte
não muda o formato de saída. Ver person_crop.py.

Saída: .npy float32 com formato (frames, 75, 3), normalizado conforme
docs/pose-format.md.

Um vídeo:
    python extract_keypoints.py video entrada.mp4 saida.npy

Lote, a partir de um ZIP do MINDS-Libras (retomável):
    python extract_keypoints.py zip raw/minds-libras/Sinalizador07.zip processed/minds-libras

O YOLOv8 vem ligado por padrão; `--no-yolo` roda o MediaPipe no quadro inteiro.
"""

import argparse
import sys
from pathlib import Path

import numpy as np

from person_crop import DEFAULT_MODEL, Box, Detector, YoloPersonDetector, estimate_crop

POSE_COUNT = 33
HAND_COUNT = 21
NUM_KEYPOINTS = POSE_COUNT + 2 * HAND_COUNT

LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24

DEFAULT_VOCABULARY = Path(__file__).resolve().parent / "vocabulary.json"

Reference = tuple[np.ndarray, float]


def _landmarks_to_array(
    landmarks, count: int, origin: tuple[int, int], size: tuple[int, int]
) -> np.ndarray:
    """Landmarks do MediaPipe (0..1 no recorte) em pixels do quadro original.

    `origin` é o canto do recorte no quadro original e `size` o tamanho do recorte
    em pixels do quadro original. `z` usa a escala de `x`, como o MediaPipe define.
    Landmark ausente vira zero.
    """
    if landmarks is None:
        return np.zeros((count, 3), dtype=np.float32)
    points = np.array([[p.x, p.y, p.z] for p in landmarks.landmark], dtype=np.float32)
    points[:, 0] = points[:, 0] * size[0] + origin[0]
    points[:, 1] = points[:, 1] * size[1] + origin[1]
    points[:, 2] = points[:, 2] * size[0]
    return points


def _reference(frame: np.ndarray) -> Reference | None:
    """Origem (meio dos quadris) e escala (largura dos ombros) do quadro, se houver corpo."""
    pose = frame[:POSE_COUNT]
    if not pose.any():
        return None
    scale = float(np.linalg.norm(pose[LEFT_SHOULDER][:2] - pose[RIGHT_SHOULDER][:2]))
    if scale < 1e-6:
        return None
    origin = (pose[LEFT_HIP] + pose[RIGHT_HIP]) / 2
    return origin, scale


def _normalize(frame: np.ndarray, reference: Reference | None) -> np.ndarray:
    """Normaliza um quadro em pixels. Sem referência, devolve zeros.

    Mãos sem corpo de referência não têm como entrar no espaço normalizado; o
    chamador repete a última referência válida (ver `extract`).
    """
    if reference is None:
        return np.zeros_like(frame)
    origin, scale = reference
    present = frame.any(axis=1)
    out = (frame - origin) / scale
    out[:, 1] *= -1  # imagem tem y para baixo; o formato usa y para cima
    out[:, 2] *= -1  # z positivo em direção à câmera
    out[~present] = 0.0
    return out


def _sampled_frames(video_path: Path, every: int):
    """Quadros a cada `every`, pulando a decodificação dos demais."""
    import cv2

    capture = cv2.VideoCapture(str(video_path))
    index = 0
    try:
        while capture.grab():
            if index % every == 0:
                ok, frame = capture.retrieve()
                if ok:
                    yield frame
            index += 1
    finally:
        capture.release()


def extract(
    video_path: Path,
    max_width: int = 960,
    detector: Detector | None = None,
    crop_margin: float = 0.15,
    crop_every: int = 15,
) -> np.ndarray:
    """Keypoints normalizados de um vídeo.

    Com `detector`, o vídeo é recortado em volta da pessoa. O recorte (ou o quadro
    inteiro, sem detector) é reduzido a `max_width` antes do MediaPipe.
    """
    import cv2
    import mediapipe as mp

    box: Box | None = None
    if detector is not None:
        box = estimate_crop(_sampled_frames(video_path, crop_every), detector, crop_margin)
        if box is None:
            print(f"{Path(video_path).name}: pessoa não detectada, usando o quadro inteiro", file=sys.stderr)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"não foi possível abrir {video_path}")

    frames = []
    last_reference: Reference | None = None
    with mp.solutions.holistic.Holistic(model_complexity=1) as holistic:
        while True:
            ok, bgr = capture.read()
            if not ok:
                break
            height, width = bgr.shape[:2]
            x0, y0, x1, y1 = (box.x0, box.y0, box.x1, box.y1) if box else (0, 0, width, height)
            region = bgr[y0:y1, x0:x1]
            size = (x1 - x0, y1 - y0)
            if region.shape[1] > max_width:
                region = cv2.resize(region, (max_width, round(region.shape[0] * max_width / region.shape[1])))
            result = holistic.process(cv2.cvtColor(region, cv2.COLOR_BGR2RGB))
            frame = np.concatenate(
                [
                    _landmarks_to_array(result.pose_landmarks, POSE_COUNT, (x0, y0), size),
                    _landmarks_to_array(result.left_hand_landmarks, HAND_COUNT, (x0, y0), size),
                    _landmarks_to_array(result.right_hand_landmarks, HAND_COUNT, (x0, y0), size),
                ]
            )
            last_reference = _reference(frame) or last_reference
            frames.append(_normalize(frame, last_reference))
    capture.release()

    if not frames:
        raise ValueError(f"nenhum frame lido em {video_path}")
    return np.stack(frames).astype(np.float32)


def _build_detector(args: argparse.Namespace) -> Detector | None:
    if not args.yolo:
        return None
    return YoloPersonDetector(args.yolo_model, args.yolo_confidence, args.yolo_device)


def _add_extraction_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--max-width", type=int, default=960, help="largura máxima do que entra no MediaPipe (recorte ou quadro)")
    parser.add_argument("--yolo", action=argparse.BooleanOptionalAction, default=True, help="recorta a pessoa com YOLOv8 (padrão: ligado)")
    parser.add_argument("--yolo-model", default=DEFAULT_MODEL, help="pesos do YOLOv8 (baixados na primeira execução)")
    parser.add_argument("--yolo-confidence", type=float, default=0.4)
    parser.add_argument("--yolo-device", default=None, help="ex.: cpu, 0 (GPU); padrão: automático")
    parser.add_argument("--crop-margin", type=float, default=0.15, help="margem do recorte, fração do tamanho da caixa")
    parser.add_argument("--crop-every", type=int, default=15, help="detecta a pessoa a cada N quadros para montar o recorte")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    video = commands.add_parser("video", help="um vídeo -> um .npy")
    video.add_argument("source", type=Path)
    video.add_argument("target", type=Path)
    _add_extraction_options(video)

    batch = commands.add_parser("zip", help="ZIP do MINDS-Libras -> pasta de .npy")
    batch.add_argument("zip_path", type=Path)
    batch.add_argument("out_root", type=Path)
    batch.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    batch.add_argument("--camera", default="Canon", help="pasta da câmera dentro do ZIP ('' para todas)")
    batch.add_argument("--limit", type=int, help="processa no máximo N vídeos novos (para teste)")
    _add_extraction_options(batch)

    args = parser.parse_args()
    detector = _build_detector(args)

    def run(path: Path) -> np.ndarray:
        return extract(path, args.max_width, detector, args.crop_margin, args.crop_every)

    if args.command == "video":
        keypoints = run(args.source)
        assert keypoints.shape[1:] == (NUM_KEYPOINTS, 3)
        args.target.parent.mkdir(parents=True, exist_ok=True)
        np.save(args.target, keypoints)
        print(f"{args.source.name}: {keypoints.shape[0]} frames -> {args.target}")
        return

    from minds_libras import process_zip

    counts = process_zip(
        args.zip_path,
        args.out_root,
        args.vocabulary,
        extract_fn=run,
        camera=args.camera or None,
        limit=args.limit,
    )
    print(counts)


if __name__ == "__main__":
    main()
