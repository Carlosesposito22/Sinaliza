import { describe, expect, it } from "vitest";
import { bodyAngles, HAND_BONES, liftDepth, prepareMotion, sampleBody, smoothSeries } from "./motion";
import { idlePoints, LEFT_HAND_START } from "./retarget";
import { NUM_KEYPOINTS } from "./skeleton";

function emptyFrame(): number[][] {
  return Array.from({ length: NUM_KEYPOINTS }, () => [0, 0, 0]);
}

// Quadro com ombros, braço esquerdo (cotovelo e punho), nariz e orelhas. z do MediaPipe exagerado.
function armFrame(noseX = 0, wristZ = 2): number[][] {
  const f = emptyFrame();
  f[0] = [noseX, 0.6, 2];
  f[7] = [0.2, 0.65, 0.5];
  f[8] = [-0.2, 0.65, 0.5];
  f[11] = [0.5, 0, 0.1];
  f[12] = [-0.5, 0, -0.1];
  f[13] = [0.7, -0.6, 0.9]; // braço: 0,63 em x e y
  f[15] = [0.3, -0.4, wristZ]; // antebraço: 0,45 em x e y
  return f;
}

describe("smoothSeries", () => {
  it("mantém série constante e não usa nem altera quadros ausentes", () => {
    const out = smoothSeries([1, 1, 99, 1, 1], [true, true, false, true, true], 1.5);
    expect(out[0]).toBeCloseTo(1, 6);
    expect(out[3]).toBeCloseTo(1, 6);
    expect(out[2]).toBe(99);
  });

  it("atenua um pico isolado", () => {
    const out = smoothSeries([0, 0, 0, 1, 0, 0, 0], Array(7).fill(true), 1.5);
    expect(out[3]).toBeLessThan(0.4);
    expect(out[3]).toBeGreaterThan(out[1]);
  });
});

describe("liftDepth", () => {
  it("refaz o z pelo comprimento do osso; o z do MediaPipe só dá o lado", () => {
    expect(liftDepth([0, 0, 0], [0.6, 0, 0], 1, 5)).toBeCloseTo(0.8, 3);
    expect(liftDepth([0, 0, 0], [0.6, 0, 0], 1, -5)).toBeCloseTo(-0.8, 3);
    expect(liftDepth([0, 0, 0.2], [0, 0.6, 0], 1, 5)).toBeCloseTo(1.0, 3); // soma ao z de onde o osso começa
  });

  it("osso já esticado no plano da imagem: sem profundidade", () => {
    expect(liftDepth([0, 0, 0], [1.2, 0, 0], 1, 5)).toBe(0);
  });
});

describe("prepareMotion", () => {
  const frames = Array.from({ length: 30 }, () => armFrame());
  const motion = prepareMotion({ fps: 30, layout: { pose: [0, 33], left_hand: [33, 54], right_hand: [54, 75] }, frames });

  it("acrescenta entrada, saída e pausa, começando e terminando nos braços caídos", () => {
    expect(motion.frames.length).toBe(30 + Math.round(0.35 * 30) + Math.round(0.45 * 30) + Math.round(0.8 * 30));
    expect(motion.body.length).toBe(motion.frames.length);
    const idle = idlePoints();
    expect(motion.frames[0][13]).toEqual(Array.from(idle.slice(13 * 3, 13 * 3 + 3)));
    expect(motion.frames[motion.frames.length - 1][15]).toEqual(Array.from(idle.slice(15 * 3, 15 * 3 + 3)));
  });

  it("braço e antebraço ficam com o comprimento padrão em 3D, à frente do corpo", () => {
    const f = motion.frames[Math.round(0.35 * 30) + 10];
    const length = (a: number[], b: number[]) => Math.hypot(b[0] - a[0], b[1] - a[1], b[2] - a[2]);
    expect(f[11][2]).toBe(0);
    expect(length(f[11], f[13])).toBeCloseTo(1, 2);
    expect(length(f[13], f[15])).toBeCloseTo(1, 2);
    expect(f[13][2]).toBeGreaterThan(0);
    expect(f[15][2]).toBeGreaterThan(f[13][2]);
  });

  it("dedos: cada osso da mão fica com o comprimento de referência em 3D", () => {
    const o = LEFT_HAND_START;
    const hand = Array.from({ length: 20 }, () => {
      const f = armFrame();
      // mão com todos os ossos encurtados em x e y (apontando para a câmera); z cru comprimido
      f[o] = [0.3, -0.4, 0];
      HAND_BONES.forEach(([a, b, length]) => {
        const [x, y, z] = f[o + a];
        f[o + b] = [x + length * 0.5, y + length * 0.3, z + 0.05];
      });
      return f;
    });
    const prepared = prepareMotion({ fps: 30, layout: { pose: [0, 33], left_hand: [33, 54], right_hand: [54, 75] }, frames: hand });
    const f = prepared.frames[Math.round(0.35 * 30) + 5];
    for (const [a, b, length] of HAND_BONES) {
      const [p, q] = [f[o + a], f[o + b]];
      expect(Math.hypot(q[0] - p[0], q[1] - p[1], q[2] - p[2])).toBeCloseTo(length, 3);
      expect(q[2]).toBeGreaterThan(p[2]); // o lado (para a câmera) vem do z cru
    }
  });
});

describe("bodyAngles", () => {
  it("é relativo à postura mediana: cabeça virada para +x dá guinada positiva", () => {
    const frames = [...Array(10)].map(() => armFrame(0)).concat([armFrame(0.1)]);
    const angles = bodyAngles(frames);
    expect(Math.abs(angles[0][0])).toBeLessThan(0.05);
    expect(angles[10][0]).toBeGreaterThan(0.1);
    expect(Math.abs(angles[10][3])).toBeLessThan(1e-6); // ombros parados
  });

  it("sem nariz ou orelhas: ângulos zerados", () => {
    expect(bodyAngles([emptyFrame()])[0]).toEqual([0, 0, 0, 0]);
  });

  it("sampleBody interpola entre quadros vizinhos", () => {
    const out = new Float32Array(4);
    sampleBody([[0, 0, 0, 0], [1, 2, 3, 4]], 10, 0.05, out);
    expect(Array.from(out)).toEqual([0.5, 1, 1.5, 2]);
  });
});
