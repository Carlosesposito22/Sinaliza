// Tabela de ossos do Microsoft Rocketbox (esqueleto Bip01, licença MIT) para o `Retargeter`.
// No Rocketbox, cada dedo tem três ossos: `Finger1` (base), `Finger11`, `Finger12`; o polegar
// (`Finger0`, `Finger01`, `Finger02`) conta como metacarpo, proximal e distal.
import type * as THREE from "three";
import type { BoneLookup } from "./retarget";

const SIDE_LETTER = { left: "L", right: "R" } as const;

const FINGER_INDEX: Record<string, number> = { Thumb: 0, Index: 1, Middle: 2, Ring: 3, Little: 4 };

const FINGER_PART: Record<string, string> = {
  Metacarpal: "",
  Proximal: "",
  Intermediate: "1",
  Distal: "2",
};

// Tronco e cabeça: o Bip01 tem Spine, Spine1 e Spine2 (o peito, pai das clavículas).
const BODY: Record<string, string> = { upperChest: "Bip01_Spine2", neck: "Bip01_Neck", head: "Bip01_Head" };

/** Nome padronizado (`leftIndexProximal`) -> nome do osso no Rocketbox (`Bip01_L_Finger1`), ou null. */
export function rocketboxBoneName(name: string): string | null {
  if (BODY[name]) return BODY[name];
  const match = /^(left|right)(UpperArm|LowerArm|Hand|Thumb|Index|Middle|Ring|Little)(Metacarpal|Proximal|Intermediate|Distal)?$/.exec(name);
  if (!match) return null;
  const [, side, part, phalanx] = match;
  const prefix = `Bip01_${SIDE_LETTER[side as "left" | "right"]}_`;
  if (part === "UpperArm") return `${prefix}UpperArm`;
  if (part === "LowerArm") return `${prefix}Forearm`;
  if (part === "Hand") return `${prefix}Hand`;
  if (!phalanx) return null;
  const finger = FINGER_INDEX[part];
  if (part === "Thumb") {
    // polegar: Finger0 (metacarpo), Finger01 (proximal), Finger02 (distal)
    const suffix = { Metacarpal: "", Proximal: "1", Distal: "2" }[phalanx];
    return suffix === undefined ? null : `${prefix}Finger0${suffix}`;
  }
  if (phalanx === "Metacarpal") return null;
  return `${prefix}Finger${finger}${FINGER_PART[phalanx]}`;
}

/** `BoneLookup` que procura os ossos pelo nome dentro do modelo carregado. */
export function rocketboxLookup(root: THREE.Object3D): BoneLookup {
  const cache = new Map<string, THREE.Object3D | null>();
  return (name) => {
    if (cache.has(name)) return cache.get(name) ?? null;
    const target = rocketboxBoneName(name);
    const node = target ? root.getObjectByName(target) ?? null : null;
    cache.set(name, node);
    return node;
  };
}
