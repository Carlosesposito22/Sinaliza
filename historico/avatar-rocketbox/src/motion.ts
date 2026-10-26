// Preparo da sequência de poses para o avatar, feito uma vez quando a resposta da API chega.
//
// Os keypoints do MediaPipe têm x e y confiáveis, mas o z do corpo é exagerado (cerca de 3 vezes
// a profundidade real) e muito ruidoso (variação de um quadro para o outro 15 vezes maior que a de
// x e y, medida no arquivo de movimentos do V-LIBRASIL). Usado direto, ele joga o antebraço para a
// câmera, dobra o punho e faz o braço tremer. Aqui:
//
// 1. cada ponto é suavizado no tempo (gaussiana centrada, sem atraso);
// 2. o z do braço e de cada osso da mão é refeito pelo comprimento do osso: com x e y medidos e o
//    comprimento conhecido, z = ±√(L² − dx² − dy²); do MediaPipe só vem o lado (frente ou trás);
// 3. os ângulos de cabeça e tronco saem do nariz, das orelhas e dos ombros, relativos à postura
//    mediana da sequência (só o movimento, não a postura de cada pessoa);
// 4. a sequência ganha uma entrada (dos braços caídos até o primeiro quadro), uma saída e uma pausa
//    em repouso, para o laço recomeçar sem salto.
//
// O formato de pose (docs/pose-format.md) não muda: isto é só como o front o interpreta.
import type { PoseSequence } from "./api";
import { NUM_KEYPOINTS } from "./skeleton";
import { idlePoints, LEFT_HAND_START, RIGHT_HAND_START } from "./retarget";

const NOSE = 0;
const LEFT_EAR = 7;
const RIGHT_EAR = 8;
const LEFT_SHOULDER = 11;
const RIGHT_SHOULDER = 12;
const POSE_COUNT = 33;

// Comprimento do braço e do antebraço em larguras de ombro: 99º percentil do comprimento em x e y
// no V-LIBRASIL (1,00 a 1,05). A sequência pode pedir mais, nunca menos.
export const DEFAULT_BONE_LENGTH = 1.0;
// Sem os três pontos do braço não dá para refazer o z: usa o do MediaPipe reduzido a ~1/3.
const FALLBACK_Z_SCALE = 0.35;
// Escala (larguras de ombro) em que o z do MediaPipe passa a decidir o lado com certeza.
const DEPTH_SIGN_SOFTNESS = 0.15;
// Na mão a diferença de z crua entre as pontas de um osso tem mediana 0,025 (só 9% abaixo de 0,005).
const HAND_DEPTH_SIGN_SOFTNESS = 0.008;

// Ossos da mão (índices dentro da mão, 0 = punho), do punho para a ponta, e o comprimento de
// referência em larguras de ombro: 99º percentil do comprimento em x e y no V-LIBRASIL (as duas
// mãos dão o mesmo). O z da mão do MediaPipe é comprimido (o mesmo osso varia de 0,34 a 0,76 da
// palma em 3D), então ele é refeito como no braço.
export const HAND_BONES: [number, number, number][] = [
  [0, 1, 0.174], [1, 2, 0.156], [2, 3, 0.128], [3, 4, 0.101],
  [0, 5, 0.376], [5, 6, 0.19], [6, 7, 0.109], [7, 8, 0.087],
  [0, 9, 0.36], [9, 10, 0.211], [10, 11, 0.122], [11, 12, 0.095],
  [0, 13, 0.33], [13, 14, 0.196], [14, 15, 0.112], [15, 16, 0.088],
  [0, 17, 0.306], [17, 18, 0.155], [18, 19, 0.086], [19, 20, 0.073],
];

const SIGMA_BODY = 1.5; // quadros
const SIGMA_HAND = 1.0;
const SIGMA_DEPTH = 3.0;
const SIGMA_HAND_DEPTH = 1.5;
const SIGMA_ANGLES = 2.0;

// Distância do nariz ao eixo entre as orelhas, em larguras entre orelhas (aproximação de cabeça adulta).
const NOSE_DEPTH = 0.55;
const DEG = Math.PI / 180;
const LIMITS = { yaw: 30 * DEG, pitch: 20 * DEG, roll: 15 * DEG, chestRoll: 6 * DEG };

const INTRO_SECONDS = 0.35;
const OUTRO_SECONDS = 0.45;
const HOLD_SECONDS = 0.8;

/** Ângulos de cabeça e tronco (radianos), relativos à postura mediana: [guinada, inclinação, rolagem, rolagem do peito]. */
export type BodyAngles = [number, number, number, number];

export interface PreparedMotion {
  fps: number;
  frames: number[][][];
  body: BodyAngles[];
}

type Frame = number[][];

const ARMS = [
  { shoulder: LEFT_SHOULDER, elbow: 13, wrist: 15, hand: LEFT_HAND_START },
  { shoulder: RIGHT_SHOULDER, elbow: 14, wrist: 16, hand: RIGHT_HAND_START },
];

function missing(p: number[]): boolean {
  return p[0] === 0 && p[1] === 0 && p[2] === 0;
}

function gaussianKernel(sigma: number): number[] {
  const radius = Math.ceil(sigma * 3);
  return Array.from({ length: radius * 2 + 1 }, (_, i) => Math.exp(-((i - radius) ** 2) / (2 * sigma * sigma)));
}

/** Suaviza no tempo a série `values` (um valor por quadro); quadros com `present` falso não entram nem mudam. */
export function smoothSeries(values: number[], present: boolean[], sigma: number): number[] {
  const kernel = gaussianKernel(sigma);
  const radius = (kernel.length - 1) / 2;
  return values.map((value, t) => {
    if (!present[t]) return value;
    let sum = 0;
    let weight = 0;
    for (let j = -radius; j <= radius; j++) {
      const s = t + j;
      if (s < 0 || s >= values.length || !present[s]) continue;
      sum += values[s] * kernel[j + radius];
      weight += kernel[j + radius];
    }
    return sum / weight;
  });
}

function smoothPoint(frames: Frame[], index: number, sigma: number, channels = [0, 1, 2]): void {
  const present = frames.map((f) => !missing(f[index]));
  for (const c of channels) {
    const smoothed = smoothSeries(frames.map((f) => f[index][c]), present, sigma);
    frames.forEach((f, t) => {
      if (present[t]) f[index][c] = smoothed[t];
    });
  }
}

function length2d(a: number[], b: number[]): number {
  return Math.hypot(b[0] - a[0], b[1] - a[1]);
}

function percentile(values: number[], q: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor(q * (sorted.length - 1)))];
}

/** Comprimento do osso na sequência: o maior visto em x e y (98º percentil), com `floor` como piso. */
function boneLength(frames: Frame[], from: number, to: number, floor = DEFAULT_BONE_LENGTH): number {
  const lengths = frames.filter((f) => !missing(f[from]) && !missing(f[to])).map((f) => length2d(f[from], f[to]));
  return Math.max(floor, percentile(lengths, 0.98));
}

/** z de `to` a partir de `from`, pelo comprimento do osso; `rawDepth` (z do MediaPipe) só dá o lado. */
export function liftDepth(from: number[], to: number[], length: number, rawDepth: number, softness = DEPTH_SIGN_SOFTNESS): number {
  const planar = length2d(from, to);
  const depth = Math.sqrt(Math.max(length * length - planar * planar, 0));
  return from[2] + depth * Math.tanh(rawDepth / softness);
}

/** z de cada ponto da mão refeito do punho para a ponta, osso a osso (o punho da mão fica onde está). */
function liftHands(frames: Frame[], raw: Frame[]): void {
  for (const start of [LEFT_HAND_START, RIGHT_HAND_START]) {
    const lengths = HAND_BONES.map(([a, b, floor]) => boneLength(frames, start + a, start + b, floor));
    frames.forEach((f, t) => {
      HAND_BONES.forEach(([a, b], i) => {
        const from = f[start + a];
        const to = f[start + b];
        if (missing(from) || missing(to)) return;
        const rawDepth = raw[t][start + b][2] - raw[t][start + a][2];
        to[2] = liftDepth(from, to, lengths[i], rawDepth, HAND_DEPTH_SIGN_SOFTNESS);
      });
    });
  }
}

function liftArms(frames: Frame[], raw: Frame[]): void {
  for (const arm of ARMS) {
    const upper = boneLength(frames, arm.shoulder, arm.elbow);
    const lower = boneLength(frames, arm.elbow, arm.wrist);
    frames.forEach((f, t) => {
      const r = raw[t];
      const handWristZ = f[arm.hand][2];
      const complete = [arm.shoulder, arm.elbow, arm.wrist].every((i) => !missing(f[i]));
      if (complete) {
        f[arm.shoulder][2] = 0; // origem nos ombros: o z do ombro é só ruído
        f[arm.elbow][2] = liftDepth(f[arm.shoulder], f[arm.elbow], upper, r[arm.elbow][2] - r[arm.shoulder][2]);
        f[arm.wrist][2] = liftDepth(f[arm.elbow], f[arm.wrist], lower, r[arm.wrist][2] - r[arm.elbow][2]);
      } else {
        for (const i of [arm.shoulder, arm.elbow, arm.wrist]) f[i][2] *= FALLBACK_Z_SCALE;
      }
      // a mão tem z próprio (relativo ao punho dela, na escala de x): só a encaixa no punho do braço
      if (!missing(f[arm.hand]) && !missing(f[arm.wrist])) {
        const shift = f[arm.wrist][2] - handWristZ;
        for (let i = arm.hand; i < arm.hand + 21; i++) if (!missing(f[i])) f[i][2] += shift;
      }
    });
  }
}

function median(values: number[]): number {
  return percentile(values, 0.5);
}

function clamp(value: number, limit: number): number {
  return Math.max(-limit, Math.min(limit, value));
}

/** Ângulos crus de um quadro, ou null se faltar nariz, orelha ou ombro. */
function rawAngles(f: Frame): BodyAngles | null {
  const nose = f[NOSE];
  const left = f[LEFT_EAR];
  const right = f[RIGHT_EAR];
  const ls = f[LEFT_SHOULDER];
  const rs = f[RIGHT_SHOULDER];
  if ([nose, left, right, ls, rs].some(missing)) return null;
  const earWidth = Math.max(length2d(left, right), 1e-6);
  const midX = (left[0] + right[0]) / 2;
  const midY = (left[1] + right[1]) / 2;
  const asin = (v: number) => Math.asin(Math.max(-1, Math.min(1, v)));
  return [
    asin((nose[0] - midX) / earWidth / NOSE_DEPTH), // nariz para +x: cabeça gira em torno de +y
    -asin((nose[1] - midY) / earWidth / NOSE_DEPTH), // nariz para cima: rotação negativa em torno de +x
    Math.atan2(left[1] - right[1], left[0] - right[0]), // orelha esquerda (em +x) mais alta: rotação em torno de +z
    Math.atan2(ls[1] - rs[1], ls[0] - rs[0]),
  ];
}

export function bodyAngles(frames: Frame[]): BodyAngles[] {
  const raw = frames.map(rawAngles);
  const present = raw.map((a) => a !== null);
  const limits = [LIMITS.yaw, LIMITS.pitch, LIMITS.roll, LIMITS.chestRoll];
  const channels = limits.map((limit, c) => {
    const values = raw.map((a) => (a ? a[c] : 0));
    const base = median(values.filter((_, t) => present[t]));
    const relative = values.map((v, t) => (present[t] ? clamp(v - base, limit) : 0));
    return smoothSeries(relative, present, SIGMA_ANGLES);
  });
  return frames.map((_, t) => [channels[0][t], channels[1][t], channels[2][t], channels[3][t]]);
}

function smoothstep(t: number): number {
  return t * t * (3 - 2 * t);
}

/** Quadro entre `a` e `b` (peso `w` de `b`); ponto ausente de um lado fica com o outro. */
function blend(a: Frame, b: Frame, w: number): Frame {
  return a.map((pa, k) => {
    const pb = b[k];
    if (missing(pa)) return [...pb];
    if (missing(pb)) return [...pa];
    return [0, 1, 2].map((c) => pa[c] + (pb[c] - pa[c]) * w);
  });
}

function idleFrame(): Frame {
  const points = idlePoints();
  return Array.from({ length: NUM_KEYPOINTS }, (_, k) => [points[k * 3], points[k * 3 + 1], points[k * 3 + 2]]);
}

export function prepareMotion(pose: PoseSequence): PreparedMotion {
  const { fps } = pose;
  const raw = pose.frames.map((f) => f.map((p) => [...p]));
  const frames = raw.map((f) => f.map((p) => [...p]));
  for (let k = 0; k < NUM_KEYPOINTS; k++) {
    smoothPoint(frames, k, k < POSE_COUNT ? SIGMA_BODY : SIGMA_HAND);
    smoothPoint(raw, k, k < POSE_COUNT ? SIGMA_DEPTH : SIGMA_HAND_DEPTH, [2]); // só o z cru, para decidir frente ou trás
  }
  liftHands(frames, raw);
  liftArms(frames, raw);
  const body = bodyAngles(frames);
  if (frames.length === 0) return { fps, frames, body };

  const idle = idleFrame();
  const rest: BodyAngles = [0, 0, 0, 0];
  const first = frames[0];
  const last = frames[frames.length - 1];
  const intro = Math.round(INTRO_SECONDS * fps);
  const outro = Math.round(OUTRO_SECONDS * fps);
  const hold = Math.round(HOLD_SECONDS * fps);
  const outFrames: Frame[] = [];
  const outBody: BodyAngles[] = [];
  const mix = (a: BodyAngles, b: BodyAngles, w: number) => a.map((v, c) => v + (b[c] - v) * w) as BodyAngles;
  for (let i = 0; i < intro; i++) {
    const w = smoothstep(i / intro);
    outFrames.push(blend(idle, first, w));
    outBody.push(mix(rest, body[0], w));
  }
  outFrames.push(...frames);
  outBody.push(...body);
  for (let i = 1; i <= outro; i++) {
    const w = smoothstep(i / outro);
    // o repouso não tem mãos: a forma da mão segue até o fim da saída e some na pausa
    outFrames.push(blend(last, idle, w));
    outBody.push(mix(body[body.length - 1], rest, w));
  }
  for (let i = 0; i < hold; i++) {
    outFrames.push(idle.map((p) => [...p]));
    outBody.push([...rest]);
  }
  return { fps, frames: outFrames, body: outBody };
}

/** Ângulos de cabeça e tronco no instante `time` (s), em laço, interpolados entre quadros. */
export function sampleBody(body: BodyAngles[], fps: number, time: number, out: Float32Array): void {
  const n = body.length;
  if (n === 0) {
    out.fill(0);
    return;
  }
  const position = (time * fps) % n;
  const i0 = Math.floor(position);
  const i1 = (i0 + 1) % n;
  const w = position - i0;
  for (let c = 0; c < 4; c++) out[c] = body[i0][c] + (body[i1][c] - body[i0][c]) * w;
}
