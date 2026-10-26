import { describe, expect, it } from "vitest";
import * as THREE from "three";
import {
  idlePoints,
  isMissing,
  palmFrame,
  samplePose,
  swingOver,
  twistAbout,
  twistBetween,
  constrainFinger,
  limitBend,
  Retargeter,
  LEFT_HAND_START,
  RIGHT_HAND_START,
} from "./retarget";
import { rocketboxBoneName } from "./rocketbox";
import { NUM_KEYPOINTS } from "./skeleton";

const v = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

function close(a: THREE.Vector3, b: THREE.Vector3, tolerance = 1e-5) {
  expect(a.distanceTo(b)).toBeLessThan(tolerance);
}

function emptyFrame(): number[][] {
  return Array.from({ length: NUM_KEYPOINTS }, () => [0, 0, 0]);
}

describe("samplePose", () => {
  it("interpola entre quadros vizinhos e volta ao início no fim", () => {
    const a = emptyFrame();
    const b = emptyFrame();
    a[11] = [0, 0, 0.1];
    a[12] = [1, 1, 1];
    b[11] = [2, 2, 0.1];
    b[12] = [3, 3, 1];
    const out = new Float32Array(NUM_KEYPOINTS * 3);

    samplePose([a, b], 10, 0.05, out); // meio caminho entre o quadro 0 e o 1
    expect(Array.from(out.slice(12 * 3, 12 * 3 + 3))).toEqual([2, 2, 1]);

    samplePose([a, b], 10, 0.15, out); // entre o quadro 1 e o 0 (laço)
    expect(out[12 * 3]).toBeCloseTo(2, 5);
  });

  it("não varre ponto ausente até a origem: usa o lado presente", () => {
    const a = emptyFrame();
    const b = emptyFrame();
    b[33] = [4, 4, 4];
    const out = new Float32Array(NUM_KEYPOINTS * 3);
    samplePose([a, b], 10, 0.05, out);
    expect(Array.from(out.slice(33 * 3, 33 * 3 + 3))).toEqual([4, 4, 4]);
    expect(isMissing(out, 34)).toBe(true); // ausente nos dois continua ausente
  });
});

describe("swingOver", () => {
  it("leva a direção de repouso até o alvo", () => {
    const q = swingOver(new THREE.Quaternion(), v(1, 0, 0), v(0, -1, 0));
    close(v(1, 0, 0).applyQuaternion(q), v(0, -1, 0));
  });

  it("é relativo ao osso pai: o giro do pai é mantido", () => {
    const parent = new THREE.Quaternion().setFromAxisAngle(v(1, 0, 0), Math.PI / 2); // gira em torno do próprio eixo
    const q = swingOver(parent, v(1, 0, 0), v(0, -1, 0));
    close(v(1, 0, 0).applyQuaternion(q), v(0, -1, 0));
    // um ponto fora do eixo do osso acompanha o giro do pai: z+ gira para y+ e depois é varrido para -y no eixo
    const side = v(0, 0, 1).applyQuaternion(q);
    expect(Math.abs(side.dot(v(0, -1, 0)))).toBeLessThan(1e-5); // continua perpendicular ao osso
  });
});

describe("palmFrame e twistBetween", () => {
  it("palma da mão esquerda em repouso: dedos em +x, palma para baixo", () => {
    const frame = palmFrame(v(0, 0, 0), v(0.08, 0, 0.02), v(0.09, 0, 0), v(0.075, 0, -0.02));
    close(frame.forward, v(1, 0, 0));
    close(frame.normal, v(0, -1, 0));
  });

  it("twistBetween gira em torno do eixo e ignora a componente ao longo dele", () => {
    const q = twistBetween(v(1, 0, 0), v(0, 1, 0), v(0, 0, 1));
    close(v(0, 1, 0).applyQuaternion(q), v(0, 0, 1));
    close(v(1, 0, 0).applyQuaternion(q), v(1, 0, 0));
    expect(twistBetween(v(1, 0, 0), v(1, 0, 0), v(0, 1, 0)).w).toBeCloseTo(1, 5); // sem componente perpendicular
  });

  it("twistAbout separa o giro em torno do eixo de uma rotação composta", () => {
    const twist = new THREE.Quaternion().setFromAxisAngle(v(1, 0, 0), 0.8);
    const swing = new THREE.Quaternion().setFromAxisAngle(v(0, 0, 1), 0.5);
    const part = twistAbout(swing.multiply(twist), v(1, 0, 0));
    expect(2 * Math.acos(part.w)).toBeCloseTo(0.8, 5);
  });
});

describe("constrainFinger e limitBend", () => {
  // dedo apontando para +x, palma olhando para -y (volar)
  const base = v(1, 0, 0);
  const volar = v(0, -1, 0);
  const angleIn = (dir: THREE.Vector3, along: THREE.Vector3, toward: THREE.Vector3) => Math.atan2(dir.dot(toward), dir.dot(along));

  it("dedo esticado continua esticado", () => {
    const [d1, d2, d3] = constrainFinger(base, volar, [v(1, 0, 0), v(1, 0, 0), v(1, 0, 0)]);
    close(d1, v(1, 0, 0));
    close(d2, v(1, 0, 0));
    close(d3, v(1, 0, 0));
  });

  it("junta do meio é dobradiça: a parte lateral da medida sai", () => {
    // falange do meio dobrada 60° para a palma e 30° para o lado (impossível)
    const bent = v(Math.cos(Math.PI / 3), -Math.sin(Math.PI / 3), 0).applyAxisAngle(v(0, -1, 0), Math.PI / 6);
    const [, d2] = constrainFinger(base, volar, [v(1, 0, 0), bent.normalize(), bent]);
    expect(Math.abs(d2.z)).toBeLessThan(1e-6); // sem componente lateral (z é o lado aqui)
    expect(d2.y).toBeLessThan(-0.5); // continua dobrada para a palma
  });

  it("não dobra para trás nem passa do limite", () => {
    const back = v(Math.cos(1), Math.sin(1), 0); // 57° para o dorso da mão
    const [, d2] = constrainFinger(base, volar, [v(1, 0, 0), back, back]);
    expect(angleIn(d2, v(1, 0, 0), volar)).toBeCloseTo(-5 * (Math.PI / 180), 5);
    const [d1] = constrainFinger(base, volar, [v(0, 0, 1), v(0, 0, 1), v(0, 0, 1)]); // base aberta 90° para o lado
    expect(Math.asin(Math.abs(d1.z))).toBeCloseTo(20 * (Math.PI / 180), 5);
  });

  it("a ponta acompanha a junta do meio", () => {
    const pip = v(0, -1, 0); // 90° na junta do meio
    const [, d2, d3] = constrainFinger(base, volar, [v(1, 0, 0), pip, pip]); // ponta medida reta
    close(d2, pip);
    expect(d2.angleTo(d3)).toBeCloseTo(0.5 * (2 / 3) * (Math.PI / 2), 5);
  });

  it("limitBend corta a dobra no máximo", () => {
    close(limitBend(v(1, 0, 0), v(0, 1, 0), Math.PI / 4), v(Math.SQRT1_2, Math.SQRT1_2, 0));
    close(limitBend(v(1, 0, 0), v(1, 1, 0).normalize(), Math.PI / 2), v(1, 1, 0).normalize());
  });
});

// Um esqueleto mínimo em pose T, olhando para +z. `skewed` dá a cada osso uma rotação de repouso
// diferente (como num FBX de verdade), mantendo as posições: o resultado tem que ser o mesmo.
function fakeRig(skewed: boolean): { root: THREE.Object3D; lookup: (name: string) => THREE.Object3D | null; bone: (name: string) => THREE.Object3D; delta: (name: string) => THREE.Quaternion } {
  const root = new THREE.Group();
  const nodes = new Map<string, THREE.Object3D>();
  const rest = new Map<string, THREE.Quaternion>();
  let counter = 0;
  const add = (name: string, parent: THREE.Object3D, worldOffset: [number, number, number]) => {
    const node = new THREE.Object3D();
    const parentWorld = parent.getWorldQuaternion(new THREE.Quaternion());
    const worldQuat = skewed
      ? new THREE.Quaternion().setFromEuler(new THREE.Euler(0.5 + counter * 0.37, 0.3 * counter, 1.1 - counter * 0.21))
      : new THREE.Quaternion();
    counter++;
    node.quaternion.copy(parentWorld.clone().invert().multiply(worldQuat));
    node.position.copy(new THREE.Vector3(...worldOffset).applyQuaternion(parentWorld.clone().invert()));
    parent.add(node);
    parent.updateMatrixWorld(true);
    node.updateMatrixWorld(true);
    nodes.set(name, node);
    rest.set(name, worldQuat);
    return node;
  };
  const hips = add("hips", root, [0, 1, 0]);
  const chest = add("upperChest", hips, [0, 0.4, 0]);
  for (const [side, sign] of [["left", 1], ["right", -1]] as const) {
    const shoulder = add(`${side}UpperArm`, chest, [sign * 0.2, 0, 0]);
    const elbow = add(`${side}LowerArm`, shoulder, [sign * 0.3, 0, 0]);
    const hand = add(`${side}Hand`, elbow, [sign * 0.25, 0, 0]);
    add(`${side}IndexProximal`, hand, [sign * 0.08, 0, 0.02]);
    add(`${side}MiddleProximal`, hand, [sign * 0.09, 0, 0]);
    add(`${side}RingProximal`, hand, [sign * 0.085, 0, -0.01]);
    add(`${side}LittleProximal`, hand, [sign * 0.075, 0, -0.02]);
    for (const name of ["Index", "Middle", "Ring", "Little"]) {
      const proximal = nodes.get(`${side}${name}Proximal`)!;
      const intermediate = add(`${side}${name}Intermediate`, proximal, [sign * 0.03, 0, 0]);
      add(`${side}${name}Distal`, intermediate, [sign * 0.025, 0, 0]);
    }
    const metacarpal = add(`${side}ThumbMetacarpal`, hand, [sign * 0.03, 0, 0.03]);
    const proximalThumb = add(`${side}ThumbProximal`, metacarpal, [sign * 0.02, 0, 0.02]);
    add(`${side}ThumbDistal`, proximalThumb, [sign * 0.02, 0, 0.02]);
  }
  const neck = add("neck", chest, [0, 0.05, 0]);
  add("head", neck, [0, 0.1, 0]);
  root.updateMatrixWorld(true);
  return {
    root,
    lookup: (name) => nodes.get(name) ?? null,
    bone: (name) => nodes.get(name)!,
    // rotação do osso em relação ao repouso, no mundo
    delta: (name) => nodes.get(name)!.getWorldQuaternion(new THREE.Quaternion()).multiply(rest.get(name)!.clone().invert()),
  };
}

const direction = (from: THREE.Object3D, to: THREE.Object3D) =>
  to.getWorldPosition(new THREE.Vector3()).sub(from.getWorldPosition(new THREE.Vector3())).normalize();

describe.each([
  ["eixos alinhados", false],
  ["eixos de repouso diferentes em cada osso", true],
])("Retargeter (%s)", (_label, skewed) => {
  const make = (zScale = 1) => {
    const rig = fakeRig(skewed);
    return { ...rig, retargeter: new Retargeter(rig.root, rig.lookup, zScale) };
  };

  it("braços caídos: o braço e o antebraço apontam para baixo, mantendo o comprimento", () => {
    const { root, bone, retargeter } = make();
    retargeter.apply(idlePoints());
    root.updateMatrixWorld(true);

    close(direction(bone("leftUpperArm"), bone("leftLowerArm")), v(0.08, -0.8, 0.05).normalize(), 1e-4);
    close(direction(bone("leftLowerArm"), bone("leftHand")), v(0.02, -0.75, 0.07).normalize(), 1e-4);
    // o comprimento do osso não muda (só gira)
    const length = bone("leftLowerArm").getWorldPosition(new THREE.Vector3()).distanceTo(bone("leftUpperArm").getWorldPosition(new THREE.Vector3()));
    expect(length).toBeCloseTo(0.3, 5);
    // lado direito espelhado
    close(direction(bone("rightUpperArm"), bone("rightLowerArm")), v(-0.08, -0.8, 0.05).normalize(), 1e-4);
  });

  it("mão como no repouso: a mão não gira; dedos esticados seguem o eixo da mão", () => {
    const { root, bone, delta, retargeter } = make();
    const points = idlePoints();
    // braços na pose T e mão esquerda com a geometria do repouso, em +x
    const set = (i: number, p: [number, number, number]) => points.set(p, i * 3);
    set(11, [0.2, 0, 0]);
    set(13, [0.5, 0, 0]);
    set(15, [0.75, 0, 0]);
    const o = LEFT_HAND_START;
    set(o + 0, [0.75, 0, 0]);
    set(o + 5, [0.83, 0, 0.02]);
    set(o + 6, [0.86, 0, 0.02]);
    set(o + 7, [0.885, 0, 0.02]);
    set(o + 8, [0.91, 0, 0.02]);
    set(o + 9, [0.84, 0, 0]);
    set(o + 17, [0.825, 0, -0.02]);
    retargeter.apply(points);
    root.updateMatrixWorld(true);

    expect(Math.abs(delta("leftHand").w)).toBeGreaterThan(0.9999);
    close(direction(bone("leftIndexProximal"), bone("leftIndexIntermediate")), v(1, 0, 0), 1e-4);
  });

  it("mão virada: girar a palma 90° em torno do eixo da mão gira a mão do avatar junto", () => {
    const { root, delta, retargeter } = make();
    const points = idlePoints();
    const set = (i: number, p: [number, number, number]) => points.set(p, i * 3);
    set(11, [0.2, 0, 0]);
    set(13, [0.5, 0, 0]);
    set(15, [0.75, 0, 0]);
    const o = LEFT_HAND_START;
    // palma de lado: o lado (mindinho → indicador) aponta para +y em vez de +z
    set(o + 0, [0.75, 0, 0]);
    set(o + 5, [0.83, 0.02, 0]);
    set(o + 9, [0.84, 0, 0]);
    set(o + 17, [0.825, -0.02, 0]);
    retargeter.apply(points);
    root.updateMatrixWorld(true);

    const lateral = v(0, 0, 1).applyQuaternion(delta("leftHand")); // o "lado" do avatar em repouso era +z
    close(lateral, v(0, 1, 0), 1e-4);
  });

  it("mão não detectada: a mão acompanha o antebraço e os dedos voltam ao repouso", () => {
    const { root, bone, delta, retargeter } = make();
    retargeter.apply(idlePoints()); // sem mãos
    root.updateMatrixWorld(true);
    expect(delta("leftLowerArm").angleTo(delta("leftHand"))).toBeLessThan(1e-5);
    const restLocal = fakeRig(skewed).bone("leftIndexIntermediate").quaternion;
    expect(bone("leftIndexIntermediate").quaternion.angleTo(restLocal)).toBeLessThan(1e-5);
    expect(RIGHT_HAND_START).toBe(54);
  });

  it("cotovelo é dobradiça: com o braço para baixo e o antebraço para a frente, o braço gira para dobrar para a frente", () => {
    const { root, bone, delta, retargeter } = make();
    const points = idlePoints();
    const set = (i: number, p: [number, number, number]) => points.set(p, i * 3);
    set(11, [0.2, 0, 0]);
    set(13, [0.2, -0.3, 0]);
    set(15, [0.2, -0.3, 0.25]);
    retargeter.apply(points);
    root.updateMatrixWorld(true);

    close(direction(bone("leftUpperArm"), bone("leftLowerArm")), v(0, -1, 0), 1e-4);
    close(direction(bone("leftLowerArm"), bone("leftHand")), v(0, 0, 1), 1e-4);
    // eixo de flexão em repouso: braço (+x) × frente (+z) = -y; agora tem que ser braço (-y) × antebraço (+z) = -x
    close(v(0, -1, 0).applyQuaternion(delta("leftUpperArm")), v(-1, 0, 0), 1e-4);
    // o antebraço só flexiona: gira em torno desse eixo em relação ao braço
    const relative = delta("leftLowerArm").multiply(delta("leftUpperArm").invert());
    close(v(-1, 0, 0).applyQuaternion(relative), v(-1, 0, 0), 1e-4);
  });

  it("pronação: metade do giro da mão vai para o antebraço, sem mudar a direção dele", () => {
    const { root, bone, delta, retargeter } = make();
    const points = idlePoints();
    const set = (i: number, p: [number, number, number]) => points.set(p, i * 3);
    set(11, [0.2, 0, 0]);
    set(13, [0.5, 0, 0]);
    set(15, [0.75, 0, 0]);
    const o = LEFT_HAND_START;
    set(o + 0, [0.75, 0, 0]);
    set(o + 5, [0.83, 0.02, 0]);
    set(o + 9, [0.84, 0, 0]);
    set(o + 17, [0.825, -0.02, 0]);
    retargeter.apply(points);
    root.updateMatrixWorld(true);

    close(direction(bone("leftLowerArm"), bone("leftHand")), v(1, 0, 0), 1e-4);
    const forearmTwist = twistAbout(delta("leftLowerArm"), v(1, 0, 0));
    expect(2 * Math.acos(Math.min(1, Math.abs(forearmTwist.w)))).toBeCloseTo(Math.PI / 4, 3);
  });

  it("cabeça: a guinada gira a cabeça em torno de +y, com parte no pescoço", () => {
    const { root, delta, retargeter } = make();
    retargeter.applyBody([0.3, 0, 0, 0]);
    root.updateMatrixWorld(true);
    close(v(0, 0, 1).applyQuaternion(delta("head")), v(Math.sin(0.3), 0, Math.cos(0.3)), 1e-4);
    close(v(0, 0, 1).applyQuaternion(delta("neck")), v(Math.sin(0.12), 0, Math.cos(0.12)), 1e-4);
    retargeter.applyBody(null);
    root.updateMatrixWorld(true);
    expect(Math.abs(delta("head").w)).toBeGreaterThan(0.9999);
  });

  it("suavização (alpha < 1) anda só parte do caminho até a nova rotação", () => {
    const { root, bone, retargeter } = make();
    retargeter.apply(idlePoints(), 0.3);
    root.updateMatrixWorld(true);
    const partial = direction(bone("leftUpperArm"), bone("leftLowerArm"));
    const target = v(0.08, -0.8, 0.05).normalize();
    expect(partial.distanceTo(target)).toBeGreaterThan(0.1); // ainda longe da pose final
    for (let i = 0; i < 30; i++) retargeter.apply(idlePoints(), 0.3);
    root.updateMatrixWorld(true);
    close(direction(bone("leftUpperArm"), bone("leftLowerArm")), target, 1e-3);
  });
});

describe("rocketboxBoneName", () => {
  it("traduz braço, mão e dedos para os ossos Bip01", () => {
    expect(rocketboxBoneName("leftUpperArm")).toBe("Bip01_L_UpperArm");
    expect(rocketboxBoneName("rightLowerArm")).toBe("Bip01_R_Forearm");
    expect(rocketboxBoneName("rightHand")).toBe("Bip01_R_Hand");
    expect(rocketboxBoneName("leftIndexProximal")).toBe("Bip01_L_Finger1");
    expect(rocketboxBoneName("leftIndexIntermediate")).toBe("Bip01_L_Finger11");
    expect(rocketboxBoneName("rightLittleDistal")).toBe("Bip01_R_Finger42");
    expect(rocketboxBoneName("leftMiddleProximal")).toBe("Bip01_L_Finger2");
    expect(rocketboxBoneName("leftRingIntermediate")).toBe("Bip01_L_Finger31");
  });

  it("polegar: Finger0, Finger01, Finger02", () => {
    expect(rocketboxBoneName("leftThumbMetacarpal")).toBe("Bip01_L_Finger0");
    expect(rocketboxBoneName("leftThumbProximal")).toBe("Bip01_L_Finger01");
    expect(rocketboxBoneName("rightThumbDistal")).toBe("Bip01_R_Finger02");
  });

  it("tronco e cabeça: Spine2, Neck, Head", () => {
    expect(rocketboxBoneName("upperChest")).toBe("Bip01_Spine2");
    expect(rocketboxBoneName("neck")).toBe("Bip01_Neck");
    expect(rocketboxBoneName("head")).toBe("Bip01_Head");
  });

  it("nomes que o rig não tem viram null", () => {
    expect(rocketboxBoneName("leftUpperLeg")).toBeNull();
    expect(rocketboxBoneName("leftIndexMetacarpal")).toBeNull();
    expect(rocketboxBoneName("leftThumbIntermediate")).toBeNull();
  });
});
