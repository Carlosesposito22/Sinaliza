"""Extrai keypoints (pose + mãos) de um vídeo com MediaPipe Holistic.

Saída: .npy float32 com formato (frames, 75, 3), normalizado conforme
docs/pose-format.md.

Uso: python extract_keypoints.py entrada.mp4 saida.npy
"""

import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

POSE_COUNT = 33
HAND_COUNT = 21
NUM_KEYPOINTS = POSE_COUNT + 2 * HAND_COUNT

LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_HIP, RIGHT_HIP = 23, 24


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


def extract(video_path: Path) -> np.ndarray:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError(f"não foi possível abrir {video_path}")

    frames = []
    with mp.solutions.holistic.Holistic(model_complexity=1) as holistic:
        while True:
            ok, bgr = capture.read()
            if not ok:
                break
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
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    source, target = Path(sys.argv[1]), Path(sys.argv[2])
    keypoints = extract(source)
    assert keypoints.shape[1:] == (NUM_KEYPOINTS, 3)
    target.parent.mkdir(parents=True, exist_ok=True)
    np.save(target, keypoints)
    print(f"{source.name}: {keypoints.shape[0]} frames -> {target}")


if __name__ == "__main__":
    main()
