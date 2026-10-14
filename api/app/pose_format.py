"""Constantes do formato de pose. Ver docs/pose-format.md."""

POSE_COUNT = 33
HAND_COUNT = 21
NUM_KEYPOINTS = POSE_COUNT + 2 * HAND_COUNT

LAYOUT: dict[str, tuple[int, int]] = {
    "pose": (0, POSE_COUNT),
    "left_hand": (POSE_COUNT, POSE_COUNT + HAND_COUNT),
    "right_hand": (POSE_COUNT + HAND_COUNT, NUM_KEYPOINTS),
}
