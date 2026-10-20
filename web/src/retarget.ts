// Retargeting: transforma os 75 keypoints do formato de pose (docs/pose-format.md) em rotações
// dos ossos de um avatar com esqueleto humanoide (hoje, o Rocketbox de `rocketbox.ts`).
//
// O avatar entra por `BoneLookup` (nome padronizado do osso -> nó three.js), então outro rig só
// precisa de outra tabela de nomes. Cada osso guarda a rotação de repouso (no mundo e local):
// o rig não precisa ter os eixos alinhados nem estar na pose T.
//
// Idéia: os keypoints são posições; o avatar tem ossos com rotações. Cada osso recebe a menor
// rotação ("swing") que leva a direção dele em repouso (o osso até o filho, na pose T) até a
// direção medida nos keypoints, **relativa à rotação do osso pai**. Assim o giro do osso em
// torno de si mesmo (o "twist") acompanha o pai e o cotovelo dobra no plano certo. A mão é a
// exceção: o giro dela vem da palma (punho, base do indicador, do médio e do mindinho).
//
// O formato de pose tem x para a direita da tela, y para cima e z em direção à câmera, e
// "esquerda" é o lado do sinalizante (aparece em x positivo). O avatar está de frente para a
// câmera, então a esquerda dele também fica em x positivo: não há espelhamento.
import * as THREE from "three";
import { NUM_KEYPOINTS } from "./skeleton";

export const POSE_LEFT_SHOULDER = 11;
export const POSE_RIGHT_SHOULDER = 12;
export const LEFT_HAND_START = 33;
export const RIGHT_HAND_START = 54;

// Os keypoints z do MediaPipe são ruidosos; reduzi-los evita braços "para dentro da tela".
export const DEFAULT_Z_SCALE = 0.6;

type Side = "left" | "right";

/** Nome padronizado do osso, no estilo do VRM (`leftUpperArm`, `rightIndexProximal`, `leftHand`...) */
export type BoneName = string;

/** Devolve o nó do osso (ou null se o rig não tiver esse osso). */
export type BoneLookup = (name: BoneName) => THREE.Object3D | null;

interface ChainBone {
  bone: BoneName;
  from: number; // índice do keypoint onde o osso começa
  to: number; // índice do keypoint onde o osso termina
}

const HAND_OFFSET: Record<Side, number> = { left: LEFT_HAND_START, right: RIGHT_HAND_START };

// Dedos: [parte do osso, keypoint inicial, keypoint final] (índices dentro da mão, 0 = punho).
const FINGER_BONES: { name: string; bones: [string, number, number][] }[] = [
  { name: "Thumb", bones: [["Metacarpal", 1, 2], ["Proximal", 2, 3], ["Distal", 3, 4]] },
  { name: "Index", bones: [["Proximal", 5, 6], ["Intermediate", 6, 7], ["Distal", 7, 8]] },
  { name: "Middle", bones: [["Proximal", 9, 10], ["Intermediate", 10, 11], ["Distal", 11, 12]] },
  { name: "Ring", bones: [["Proximal", 13, 14], ["Intermediate", 14, 15], ["Distal", 15, 16]] },
  { name: "Little", bones: [["Proximal", 17, 18], ["Intermediate", 18, 19], ["Distal", 19, 20]] },
];

const HAND_WRIST = 0;
const HAND_INDEX_MCP = 5;
const HAND_MIDDLE_MCP = 9;
const HAND_LITTLE_MCP = 17;

/** Ponto ausente no formato de pose: [0, 0, 0]. */
export function isMissing(points: ArrayLike<number>, index: number): boolean {
  const o = index * 3;
  return points[o] === 0 && points[o + 1] === 0 && points[o + 2] === 0;
}

export function readPoint(points: ArrayLike<number>, index: number, zScale: number, out: THREE.Vector3): THREE.Vector3 {
  const o = index * 3;
  return out.set(points[o], points[o + 1], points[o + 2] * zScale);
}

/** Posição no instante `time` (s): interpola entre os dois quadros vizinhos, em laço. Escreve em `out`. */
export function samplePose(frames: number[][][], fps: number, time: number, out: Float32Array): void {
  const n = frames.length;
  const position = (time * fps) % n;
  const i0 = Math.floor(position);
  const i1 = (i0 + 1) % n;
  const w = position - i0;
  const a = frames[i0];
  const b = frames[i1];
  for (let k = 0; k < NUM_KEYPOINTS; k++) {
    const pa = a[k];
    const pb = b[k];
    const missingA = pa[0] === 0 && pa[1] === 0 && pa[2] === 0;
    const missingB = pb[0] === 0 && pb[1] === 0 && pb[2] === 0;
    for (let c = 0; c < 3; c++) {
      let value: number;
      if (missingA && missingB) value = 0;
      else if (missingA) value = pb[c];
      else if (missingB) value = pa[c];
      else value = pa[c] + (pb[c] - pa[c]) * w;
      out[k * 3 + c] = value;
    }
  }
}

/** Menor rotação que leva `from` a `to` (vetores unitários), aplicada sobre `base`: `swing * base`. */
export function swingOver(base: THREE.Quaternion, restDir: THREE.Vector3, target: THREE.Vector3): THREE.Quaternion {
  const current = restDir.clone().applyQuaternion(base).normalize();
  const swing = new THREE.Quaternion().setFromUnitVectors(current, target.clone().normalize());
  return swing.multiply(base);
}

/** Palma: frente (punho → base do médio) e normal (frente × lado, com lado = mindinho → indicador). */
export function palmFrame(
  wrist: THREE.Vector3,
  index: THREE.Vector3,
  middle: THREE.Vector3,
  little: THREE.Vector3,
): { forward: THREE.Vector3; normal: THREE.Vector3 } {
  const forward = middle.clone().sub(wrist).normalize();
  const lateral = index.clone().sub(little).normalize();
  const normal = new THREE.Vector3().crossVectors(forward, lateral).normalize();
  return { forward, normal };
}

/** Giro em torno de `axis` que leva o vetor `from` a `to` (os dois são projetados no plano ⟂ `axis`). */
export function twistBetween(axis: THREE.Vector3, from: THREE.Vector3, to: THREE.Vector3): THREE.Quaternion {
  const a = from.clone().sub(axis.clone().multiplyScalar(from.dot(axis)));
  const b = to.clone().sub(axis.clone().multiplyScalar(to.dot(axis)));
  if (a.lengthSq() < 1e-10 || b.lengthSq() < 1e-10) return new THREE.Quaternion();
  const angle = Math.atan2(axis.dot(new THREE.Vector3().crossVectors(a, b)), a.dot(b));
  return new THREE.Quaternion().setFromAxisAngle(axis, angle);
}

interface RestHand {
  forward: THREE.Vector3;
  normal: THREE.Vector3;
}

/** Aplica keypoints a um avatar. Construa com o modelo na pose de repouso (como carrega). */
export class Retargeter {
  private readonly lookup: BoneLookup;
  private readonly zScale: number;
  private readonly restDir = new Map<BoneName, THREE.Vector3>();
  private readonly restWorld = new Map<BoneName, THREE.Quaternion>();
  private readonly restLocal = new Map<BoneName, THREE.Quaternion>();
  private readonly restHand = new Map<Side, RestHand>();
  private readonly chains: Record<Side, { arm: ChainBone[]; hand: BoneName; fingers: ChainBone[] }>;

  /** `root` é um nó acima do esqueleto: as matrizes do mundo são atualizadas a partir dele. */
  constructor(root: THREE.Object3D, lookup: BoneLookup, zScale = DEFAULT_Z_SCALE) {
    this.lookup = lookup;
    this.zScale = zScale;
    root.updateMatrixWorld(true);

    this.chains = { left: this.buildChains("left"), right: this.buildChains("right") };
    for (const side of ["left", "right"] as Side[]) {
      const { arm, hand, fingers } = this.chains[side];
      const bones = [...arm, ...fingers];
      for (const { bone } of bones) this.recordRestDirection(bone, bones, hand);
      for (const name of [...bones.map((b) => b.bone), hand]) this.recordRestRotation(name);
      this.recordRestHand(side);
    }
  }

  private buildChains(side: Side) {
    const shoulder = side === "left" ? POSE_LEFT_SHOULDER : POSE_RIGHT_SHOULDER;
    const elbow = shoulder + 2;
    const wrist = shoulder + 4;
    const offset = HAND_OFFSET[side];
    const fingers: ChainBone[] = [];
    for (const finger of FINGER_BONES) {
      for (const [part, from, to] of finger.bones) {
        fingers.push({ bone: `${side}${finger.name}${part}`, from: offset + from, to: offset + to });
      }
    }
    return {
      arm: [
        { bone: `${side}UpperArm`, from: shoulder, to: elbow },
        { bone: `${side}LowerArm`, from: elbow, to: wrist },
      ],
      hand: `${side}Hand`,
      fingers,
    };
  }

  private node(name: BoneName): THREE.Object3D | null {
    return this.lookup(name);
  }

  private worldPosition(name: BoneName): THREE.Vector3 | null {
    const node = this.node(name);
    return node ? node.getWorldPosition(new THREE.Vector3()) : null;
  }

  private recordRestRotation(name: BoneName): void {
    const node = this.node(name);
    if (!node) return;
    this.restWorld.set(name, node.getWorldQuaternion(new THREE.Quaternion()));
    this.restLocal.set(name, node.quaternion.clone());
  }

  /** Direção do osso até o próximo osso da cadeia (ou até a mão), com a pose de repouso como referência. */
  private recordRestDirection(bone: BoneName, chain: ChainBone[], hand: BoneName): void {
    const here = this.worldPosition(bone);
    if (!here) return;
    const index = chain.findIndex((c) => c.bone === bone);
    let next: BoneName | null = null;
    const following = chain[index + 1];
    if (bone.endsWith("UpperArm")) next = bone.replace("UpperArm", "LowerArm");
    else if (bone.endsWith("LowerArm")) next = hand;
    else if (following && sameFinger(following.bone, bone)) next = following.bone;
    let direction: THREE.Vector3 | null = null;
    if (next) {
      const there = this.worldPosition(next);
      if (there) direction = there.sub(here).normalize();
    } else {
      // última falange: não há osso adiante, usa a direção da falange anterior
      const previous = chain[index - 1];
      const before = previous && sameFinger(previous.bone, bone) ? this.worldPosition(previous.bone) : null;
      if (before) direction = here.clone().sub(before).normalize();
    }
    if (direction) this.restDir.set(bone, direction);
  }

  private recordRestHand(side: Side): void {
    const wrist = this.worldPosition(`${side}Hand`);
    const index = this.worldPosition(`${side}IndexProximal`);
    const middle = this.worldPosition(`${side}MiddleProximal`);
    const little = this.worldPosition(`${side}LittleProximal`);
    if (wrist && index && middle && little) this.restHand.set(side, palmFrame(wrist, index, middle, little));
  }

  /** Rotação do osso em relação ao repouso, no espaço do mundo. Osso sem repouso gravado (fora da cadeia) conta como parado. */
  private delta(bone: BoneName | null): THREE.Quaternion {
    const node = bone ? this.node(bone) : null;
    const rest = bone ? this.restWorld.get(bone) : undefined;
    if (!node || !rest) return new THREE.Quaternion();
    return node.getWorldQuaternion(new THREE.Quaternion()).multiply(rest.clone().invert());
  }

  private setWorldDelta(bone: BoneName, delta: THREE.Quaternion, alpha: number): void {
    const node = this.node(bone);
    const rest = this.restWorld.get(bone);
    if (!node?.parent || !rest) return;
    const parentWorld = node.parent.getWorldQuaternion(new THREE.Quaternion());
    const world = delta.clone().multiply(rest);
    const local = parentWorld.invert().multiply(world);
    if (alpha >= 1) node.quaternion.copy(local);
    else node.quaternion.slerp(local, alpha);
    node.updateMatrixWorld(true);
  }

  /** `parentBone`: o osso da cadeia que é pai deste (null se o pai não é movido por nós, como a clavícula). */
  private aim(chainBone: ChainBone, parentBone: BoneName | null, points: ArrayLike<number>, alpha: number): void {
    const rest = this.restDir.get(chainBone.bone);
    if (!rest) return;
    if (isMissing(points, chainBone.from) || isMissing(points, chainBone.to)) return;
    const from = readPoint(points, chainBone.from, this.zScale, new THREE.Vector3());
    const to = readPoint(points, chainBone.to, this.zScale, new THREE.Vector3());
    const target = to.sub(from);
    if (target.lengthSq() < 1e-10) return;
    this.setWorldDelta(chainBone.bone, swingOver(this.delta(parentBone), rest, target), alpha);
  }

  private handPresent(side: Side, points: ArrayLike<number>): boolean {
    const o = HAND_OFFSET[side];
    return [HAND_WRIST, HAND_INDEX_MCP, HAND_MIDDLE_MCP, HAND_LITTLE_MCP].every((i) => !isMissing(points, o + i));
  }

  /** Aplica um quadro `points` (75 x 3, achatado). `alpha` < 1 suaviza (slerp para a nova rotação). */
  apply(points: ArrayLike<number>, alpha = 1): void {
    for (const side of ["left", "right"] as Side[]) {
      const { arm, hand, fingers } = this.chains[side];
      this.aim(arm[0], null, points, alpha);
      this.aim(arm[1], arm[0].bone, points, alpha);
      this.applyHand(side, hand, arm[1].bone, fingers, points, alpha);
    }
  }

  private applyHand(side: Side, handBone: BoneName, forearm: BoneName, fingers: ChainBone[], points: ArrayLike<number>, alpha: number): void {
    const rest = this.restHand.get(side);
    if (!this.node(handBone)?.parent || !rest) return;
    const parentDelta = this.delta(forearm);
    if (!this.handPresent(side, points)) {
      // mão não detectada: acompanha o antebraço e os dedos voltam ao repouso
      this.setWorldDelta(handBone, parentDelta, alpha);
      for (const { bone } of fingers) {
        const node = this.node(bone);
        const local = this.restLocal.get(bone);
        if (node && local) node.quaternion.slerp(local, alpha);
      }
      return;
    }
    const o = HAND_OFFSET[side];
    const read = (i: number) => readPoint(points, o + i, this.zScale, new THREE.Vector3());
    const target = palmFrame(read(HAND_WRIST), read(HAND_INDEX_MCP), read(HAND_MIDDLE_MCP), read(HAND_LITTLE_MCP));
    const swung = swingOver(parentDelta, rest.forward, target.forward);
    const normalNow = rest.normal.clone().applyQuaternion(swung);
    const twist = twistBetween(target.forward, normalNow, target.normal);
    this.setWorldDelta(handBone, twist.multiply(swung), alpha);
    let previous: ChainBone | null = null;
    for (const finger of fingers) {
      const parent = previous && sameFinger(previous.bone, finger.bone) ? previous.bone : handBone;
      this.aim(finger, parent, points, alpha);
      previous = finger;
    }
  }
}

function sameFinger(a: string, b: string): boolean {
  const strip = (name: string) => name.replace(/(Metacarpal|Proximal|Intermediate|Distal)$/, "");
  return strip(a) === strip(b);
}

/** Quadro de repouso (braços caídos), para o avatar parado enquanto não há animação. Sem mãos. */
export function idlePoints(): Float32Array {
  const points = new Float32Array(NUM_KEYPOINTS * 3);
  const set = (i: number, x: number, y: number, z: number) => points.set([x, y, z], i * 3);
  set(POSE_LEFT_SHOULDER, 0.5, 0, 0);
  set(POSE_RIGHT_SHOULDER, -0.5, 0, 0);
  set(13, 0.58, -0.8, 0.05);
  set(14, -0.58, -0.8, 0.05);
  set(15, 0.6, -1.55, 0.12);
  set(16, -0.6, -1.55, 0.12);
  return points;
}
