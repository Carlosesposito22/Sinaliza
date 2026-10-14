// Layout dos 75 keypoints. Ver docs/pose-format.md.
export const NUM_KEYPOINTS = 75;

const POSE_COUNT = 33;
const HAND_COUNT = 21;
const LEFT_HAND = POSE_COUNT;
const RIGHT_HAND = POSE_COUNT + HAND_COUNT;

const POSE_BONES: [number, number][] = [
  [0, 11],
  [0, 12],
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [24, 26],
  [26, 28],
];

const HAND_BONES: [number, number][] = [
  [0, 1],
  [1, 2],
  [2, 3],
  [3, 4],
  [0, 5],
  [5, 6],
  [6, 7],
  [7, 8],
  [5, 9],
  [9, 10],
  [10, 11],
  [11, 12],
  [9, 13],
  [13, 14],
  [14, 15],
  [15, 16],
  [13, 17],
  [17, 18],
  [18, 19],
  [19, 20],
  [0, 17],
];

const offset = (bones: [number, number][], by: number): [number, number][] =>
  bones.map(([a, b]) => [a + by, b + by]);

export const BONES: [number, number][] = [
  ...POSE_BONES,
  ...offset(HAND_BONES, LEFT_HAND),
  ...offset(HAND_BONES, RIGHT_HAND),
];
