"""Extrai keypoints (pose + mãos) de vídeos com MediaPipe Holistic.

Saída: .npy float32 com formato (frames, 75, 3), normalizado conforme
docs/pose-format.md.

Um vídeo:
    python extract_keypoints.py video entrada.mp4 saida.npy

Lote, a partir de um ZIP do MINDS-Libras (retomável):
    python extract_keypoints.py zip raw/minds-libras/Sinalizador07.zip processed/minds-libras
"""

import argparse
from pathlib import Path

import numpy as np

POSE_COUNT = 33
HAND_COUNT = 21
NUM_KEYPOINTS = POSE_COUNT + 2 * HAND_COUNT

LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24

DEFAULT_VOCABULARY = Path(__file__).resolve().parent / "vocabulary.json"


def _landmarks_to_array(landmarks, count: int) -> np.ndarray:
    if landmarks is None:
        return np.zeros((count, 3), dtype=np.float32)
    return np.array([[p.x, p.y, p.z] for p in landmarks.landmark], dtype=np.float32)


def _normalize(frame: np.ndarray) -> np.ndarray:
    pose = frame[:POSE_COUNT]
    if not pose.any():
        return frame
    origin = (pose[LEFT_HIP] + pose[RIGHT_HIP]) / 2
    scale = np.linalg.norm(pose[LEFT_SHOULDER][:2] - pose[RIGHT_SHOULDER][:2])
    if scale < 1e-6:
        return frame

    present = frame.any(axis=1)
    out = (frame - origin) / scale
    out[:, 1] *= -1  # imagem tem y para baixo; o formato usa y para cima
    out[:, 2] *= -1  # z positivo em direção à câmera
    out[~present] = 0.0
    return out


def extract(video_path: Path, max_width: int = 960) -> np.ndarray:
    """Keypoints normalizados de um vídeo. Frames largos são reduzidos a `max_width`."""
    import cv2
    import mediapipe as mp

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"não foi possível abrir {video_path}")

    frames = []
    with mp.solutions.holistic.Holistic(model_complexity=1) as holistic:
        while True:
            ok, bgr = capture.read()
            if not ok:
                break
            height, width = bgr.shape[:2]
            if width > max_width:
                bgr = cv2.resize(bgr, (max_width, round(height * max_width / width)))
            result = holistic.process(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            frame = np.concatenate(
                [
                    _landmarks_to_array(result.pose_landmarks, POSE_COUNT),
                    _landmarks_to_array(result.left_hand_landmarks, HAND_COUNT),
                    _landmarks_to_array(result.right_hand_landmarks, HAND_COUNT),
                ]
            )
            frames.append(_normalize(frame))
    capture.release()

    if not frames:
        raise ValueError(f"nenhum frame lido em {video_path}")
    return np.stack(frames).astype(np.float32)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)

    video = commands.add_parser("video", help="um vídeo -> um .npy")
    video.add_argument("source", type=Path)
    video.add_argument("target", type=Path)
    video.add_argument("--max-width", type=int, default=960)

    batch = commands.add_parser("zip", help="ZIP do MINDS-Libras -> pasta de .npy")
    batch.add_argument("zip_path", type=Path)
    batch.add_argument("out_root", type=Path)
    batch.add_argument("--vocabulary", type=Path, default=DEFAULT_VOCABULARY)
    batch.add_argument("--camera", default="Canon", help="pasta da câmera dentro do ZIP ('' para todas)")
    batch.add_argument("--limit", type=int, help="processa no máximo N vídeos novos (para teste)")
    batch.add_argument("--max-width", type=int, default=960)

    args = parser.parse_args()

    if args.command == "video":
        keypoints = extract(args.source, args.max_width)
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
        extract_fn=lambda path: extract(path, args.max_width),
        camera=args.camera or None,
        limit=args.limit,
    )
    print(counts)


if __name__ == "__main__":
    main()
