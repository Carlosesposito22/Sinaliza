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

// O z do braço já chega refeito por `prepareMotion` (motion.ts); aqui ele entra como está.
export const DEFAULT_Z_SCALE = 1;

// O avatar olha para +z. Na pose de repouso, o cotovelo dobra levando o antebraço para a frente.
const FORWARD = new THREE.Vector3(0, 0, 1);
// Abaixo de ~5° de dobra o plano do cotovelo é ruído; acima de ~20°, vale inteiro.
const HINGE_MIN = Math.sin(5 * (Math.PI / 180));
const HINGE_FULL = Math.sin(20 * (Math.PI / 180));
// Parte do giro da mão (pronação) que vai para o antebraço, como no braço de verdade; o resto fica no punho.
const FOREARM_TWIST_SHARE = 0.5;
// Parte da rotação da cabeça feita pelo pescoço.
const NECK_SHARE = 0.4;

// Limites anatômicos dos dedos (fora o polegar), em radianos. Flexão positiva = para a palma.
const DEG = Math.PI / 180;
const FINGER_LIMITS = {
  mcpFlex: [-30 * DEG, 95 * DEG], // base do dedo: flexiona e abre um pouco para os lados
  mcpSpread: 20 * DEG,
  pip: [-5 * DEG, 110 * DEG], // juntas do meio e da ponta: dobradiças
  dip: [-5 * DEG, 90 * DEG],
} as const;
// A junta da ponta acompanha a do meio (~2/3 dela) na mão de verdade; a medida dela é a mais ruidosa.
const DIP_COUPLING = 2 / 3;
const DIP_MEASURED_SHARE = 0.5;
// Polegar: só limita a dobra entre ossos vizinhos.
const THUMB_MAX_BEND = 75 * DEG;

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

// Ossos de tronco e cabeça movidos por `applyBody` (o rig pode não ter algum: fica parado).
const BODY_BONES: BoneName[] = ["upperChest", "neck", "head"];

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

/** Componente de `q` que gira em torno de `axis` (unitário): o "twist" da decomposição swing-twist. */
export function twistAbout(q: THREE.Quaternion, axis: THREE.Vector3): THREE.Quaternion {
  const d = q.x * axis.x + q.y * axis.y + q.z * axis.z;
  const twist = new THREE.Quaternion(axis.x * d, axis.y * d, axis.z * d, q.w);
  if (twist.lengthSq() < 1e-12) return new THREE.Quaternion();
  return twist.normalize();
}

/** Rotação que leva o par ortonormal (`a`, `b`) até (`c`, `d`). */
export function alignPair(a: THREE.Vector3, b: THREE.Vector3, c: THREE.Vector3, d: THREE.Vector3): THREE.Quaternion {
  const from = new THREE.Matrix4().makeBasis(a, b, new THREE.Vector3().crossVectors(a, b));
  const to = new THREE.Matrix4().makeBasis(c, d, new THREE.Vector3().crossVectors(c, d));
  return new THREE.Quaternion().setFromRotationMatrix(to.multiply(from.transpose()));
}

function clampRange(value: number, [min, max]: readonly [number, number]): number {
  return Math.max(min, Math.min(max, value));
}

/** `along` girado de `angle` na direção de `toward` (os dois unitários e perpendiculares). */
function rotateIn(along: THREE.Vector3, toward: THREE.Vector3, angle: number): THREE.Vector3 {
  return along.clone().multiplyScalar(Math.cos(angle)).addScaledVector(toward, Math.sin(angle));
}

/**
 * Direções possíveis para as três falanges de um dedo (indicador a mindinho), a partir das medidas.
 * `base`: punho → base do dedo; `volar`: para onde a palma olha; `measured`: as três falanges
 * medidas (unitárias). A base flexiona e abre um pouco para os lados; as juntas do meio e da ponta
 * são dobradiças que só dobram para a palma (a parte lateral da medida, que é ruído, sai).
 */
export function constrainFinger(base: THREE.Vector3, volar: THREE.Vector3, measured: THREE.Vector3[]): THREE.Vector3[] {
  const along = base.clone().addScaledVector(volar, -base.dot(volar)).normalize();
  const vol = volar.clone().addScaledVector(along, -volar.dot(along)).normalize();
  const lateral = new THREE.Vector3().crossVectors(along, vol);
  const [m1, m2, m3] = measured;

  const flex = clampRange(Math.atan2(m1.dot(vol), m1.dot(along)), FINGER_LIMITS.mcpFlex);
  const spreadLimit = FINGER_LIMITS.mcpSpread;
  const spread = Math.max(-spreadLimit, Math.min(spreadLimit, Math.asin(Math.max(-1, Math.min(1, m1.dot(lateral))))));
  const d1 = rotateIn(rotateIn(along, vol, flex), lateral, spread);
  // a "palma" do dedo depois da base (perpendicular a d1): para onde as dobradiças seguintes dobram
  const v1 = rotateIn(vol, along, -flex);

  const pip = clampRange(Math.atan2(m2.dot(v1), m2.dot(d1)), FINGER_LIMITS.pip);
  const d2 = rotateIn(d1, v1, pip);
  const v2 = rotateIn(v1, d1, -pip);

  const dipMeasured = Math.atan2(m3.dot(v2), m3.dot(d2));
  const dip = clampRange(DIP_MEASURED_SHARE * dipMeasured + (1 - DIP_MEASURED_SHARE) * DIP_COUPLING * pip, FINGER_LIMITS.dip);
  return [d1, d2, rotateIn(d2, v2, dip)];
}

/** `dir` com no máximo `maxAngle` de dobra em relação a `previous` (os dois unitários). */
export function limitBend(previous: THREE.Vector3, dir: THREE.Vector3, maxAngle: number): THREE.Vector3 {
  const angle = previous.angleTo(dir);
  if (angle <= maxAngle) return dir.clone();
  const axis = new THREE.Vector3().crossVectors(previous, dir);
  if (axis.lengthSq() < 1e-12) return dir.clone();
  return previous.clone().applyAxisAngle(axis.normalize(), maxAngle);
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
  private readonly restHinge = new Map<Side, THREE.Vector3>();
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
      const upper = this.restDir.get(arm[0].bone);
      if (upper) this.restHinge.set(side, new THREE.Vector3().crossVectors(upper, FORWARD).normalize());
    }
    for (const name of BODY_BONES) this.recordRestRotation(name);
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

  /** Direção medida do osso (de `from` a `to`), ou null se faltar ponto. */
  private measured(chainBone: ChainBone, points: ArrayLike<number>): THREE.Vector3 | null {
    if (isMissing(points, chainBone.from) || isMissing(points, chainBone.to)) return null;
    const from = readPoint(points, chainBone.from, this.zScale, new THREE.Vector3());
    const target = readPoint(points, chainBone.to, this.zScale, new THREE.Vector3()).sub(from);
    return target.lengthSq() < 1e-10 ? null : target.normalize();
  }

  /** Rotação (no mundo, relativa ao repouso) que aponta o osso para a direção medida, mantendo o giro do pai. */
  private aimDelta(
    chainBone: ChainBone,
    parentDelta: THREE.Quaternion,
    points: ArrayLike<number>,
    direction?: THREE.Vector3,
  ): THREE.Quaternion | null {
    const rest = this.restDir.get(chainBone.bone);
    const target = direction ?? this.measured(chainBone, points);
    if (!rest || !target) return null;
    return swingOver(parentDelta, rest, target);
  }

  /**
   * Braço: além de apontar para o cotovelo, gira em torno de si mesmo para o cotovelo dobrar no
   * plano certo (o cotovelo é uma dobradiça: só flexiona). Sem isso o antebraço dobra de lado.
   */
  private upperArmDelta(side: Side, points: ArrayLike<number>): THREE.Quaternion | null {
    const [upper, lower] = this.chains[side].arm;
    const swing = this.aimDelta(upper, new THREE.Quaternion(), points);
    const rest = this.restDir.get(upper.bone);
    const hinge = this.restHinge.get(side);
    const u = this.measured(upper, points);
    const f = this.measured(lower, points);
    if (!swing || !rest || !hinge || !u || !f) return swing;
    const bend = new THREE.Vector3().crossVectors(u, f);
    const amount = bend.length();
    const weight = Math.min(1, Math.max(0, (amount - HINGE_MIN) / (HINGE_FULL - HINGE_MIN)));
    if (weight <= 0) return swing;
    const hinged = alignPair(rest, hinge, u, bend.divideScalar(amount));
    return swing.slerp(hinged, weight * weight * (3 - 2 * weight));
  }

  private handPresent(side: Side, points: ArrayLike<number>): boolean {
    const o = HAND_OFFSET[side];
    return [HAND_WRIST, HAND_INDEX_MCP, HAND_MIDDLE_MCP, HAND_LITTLE_MCP].every((i) => !isMissing(points, o + i));
  }

  /** Aplica um quadro `points` (75 x 3, achatado). `alpha` < 1 suaviza (slerp para a nova rotação). */
  apply(points: ArrayLike<number>, alpha = 1): void {
    for (const side of ["left", "right"] as Side[]) {
      const { arm, hand, fingers } = this.chains[side];
      const upper = this.upperArmDelta(side, points);
      if (upper) this.setWorldDelta(arm[0].bone, upper, alpha);
      const forearm = this.aimDelta(arm[1], this.delta(arm[0].bone), points);
      this.applyHand(side, hand, arm[1].bone, forearm, fingers, points, alpha);
    }
  }

  /**
   * Cabeça e tronco: `angles` = [guinada, inclinação, rolagem, rolagem do peito] em radianos, em
   * torno dos eixos do mundo (y, x, z); null volta ao repouso. Chame antes de `apply` (o peito
   * é pai dos braços).
   */
  applyBody(angles: ArrayLike<number> | null, alpha = 1): void {
    if (!angles) {
      for (const name of BODY_BONES) {
        const node = this.node(name);
        const local = this.restLocal.get(name);
        if (node && local) node.quaternion.slerp(local, alpha);
      }
      return;
    }
    const head = new THREE.Quaternion().setFromEuler(new THREE.Euler(angles[1], angles[0], angles[2], "YXZ"));
    const chest = new THREE.Quaternion().setFromAxisAngle(FORWARD, angles[3]);
    this.setWorldDelta("upperChest", chest, alpha);
    this.setWorldDelta("neck", new THREE.Quaternion().slerp(head, NECK_SHARE), alpha);
    this.setWorldDelta("head", head, alpha);
  }

  private applyHand(
    side: Side,
    handBone: BoneName,
    forearm: BoneName,
    forearmTarget: THREE.Quaternion | null,
    fingers: ChainBone[],
    points: ArrayLike<number>,
    alpha: number,
  ): void {
    const rest = this.restHand.get(side);
    if (!this.node(handBone)?.parent || !rest || !this.handPresent(side, points)) {
      if (forearmTarget) this.setWorldDelta(forearm, forearmTarget, alpha);
      if (!this.node(handBone)?.parent) return;
      // mão não detectada: acompanha o antebraço e os dedos voltam ao repouso
      this.setWorldDelta(handBone, this.delta(forearm), alpha);
      for (const { bone } of fingers) {
        const node = this.node(bone);
        const local = this.restLocal.get(bone);
        if (node && local) node.quaternion.slerp(local, alpha);
      }
      return;
    }
    const parentDelta = forearmTarget ?? this.delta(forearm);
    const o = HAND_OFFSET[side];
    const read = (i: number) => readPoint(points, o + i, this.zScale, new THREE.Vector3());
    const target = palmFrame(read(HAND_WRIST), read(HAND_INDEX_MCP), read(HAND_MIDDLE_MCP), read(HAND_LITTLE_MCP));
    const swung = swingOver(parentDelta, rest.forward, target.forward);
    const normalNow = rest.normal.clone().applyQuaternion(swung);
    const handDelta = twistBetween(target.forward, normalNow, target.normal).multiply(swung);
    if (forearmTarget) {
      // pronação: parte do giro da mão em torno do antebraço passa para o antebraço (que não muda de direção)
      const axis = this.restDir.get(forearm)?.clone().applyQuaternion(forearmTarget).normalize();
      const extra = handDelta.clone().multiply(forearmTarget.clone().invert());
      const share = axis ? new THREE.Quaternion().slerp(twistAbout(extra, axis), FOREARM_TWIST_SHARE) : new THREE.Quaternion();
      this.setWorldDelta(forearm, share.multiply(forearmTarget), alpha);
    }
    this.setWorldDelta(handBone, handDelta, alpha);
    // a palma olha para +normal na mão esquerda e para −normal na direita (palmFrame é espelhado)
    const volar = side === "left" ? target.normal : target.normal.clone().negate();
    const directions = this.fingerDirections(side, points, volar);
    let previous: ChainBone | null = null;
    for (const finger of fingers) {
      const parent = previous && sameFinger(previous.bone, finger.bone) ? previous.bone : handBone;
      const delta = this.aimDelta(finger, this.delta(parent), points, directions.get(finger.bone));
      if (delta) this.setWorldDelta(finger.bone, delta, alpha);
      previous = finger;
    }
  }

  /** Direções das falanges já com os limites anatômicos; dedo com ponto ausente fica de fora (usa a medida). */
  private fingerDirections(side: Side, points: ArrayLike<number>, volar: THREE.Vector3): Map<BoneName, THREE.Vector3> {
    const o = HAND_OFFSET[side];
    const directions = new Map<BoneName, THREE.Vector3>();
    const point = (i: number) => readPoint(points, o + i, this.zScale, new THREE.Vector3());
    for (const finger of FINGER_BONES) {
      const indices = [finger.bones[0][1], ...finger.bones.map(([, , to]) => to)];
      if (indices.some((i) => isMissing(points, o + i)) || isMissing(points, o + HAND_WRIST)) continue;
      const measured = finger.bones.map(([, from, to]) => point(to).sub(point(from)).normalize());
      let constrained: THREE.Vector3[];
      if (finger.name === "Thumb") {
        const second = limitBend(measured[0], measured[1], THUMB_MAX_BEND);
        constrained = [measured[0], second, limitBend(second, measured[2], THUMB_MAX_BEND)];
      } else {
        const base = point(finger.bones[0][1]).sub(point(HAND_WRIST));
        if (base.lengthSq() < 1e-10) continue;
        constrained = constrainFinger(base.normalize(), volar, measured);
      }
      finger.bones.forEach(([part], i) => directions.set(`${side}${finger.name}${part}`, constrained[i]));
    }
    return directions;
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
