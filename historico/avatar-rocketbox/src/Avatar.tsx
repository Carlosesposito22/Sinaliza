import { useState } from "react";
import type { PoseSequence } from "./api";
import { RocketboxAvatar } from "./RocketboxAvatar";
import { SkeletonAvatar } from "./SkeletonAvatar";

interface AvatarProps {
  pose: PoseSequence | null;
}

// Avatar 3D (Rocketbox). Se o modelo não carregar (arquivo ausente, WebGL sem suporte), cai no esqueleto.
export function Avatar({ pose }: AvatarProps) {
  const [failed, setFailed] = useState(false);
  if (failed) return <SkeletonAvatar pose={pose} />;
  return <RocketboxAvatar pose={pose} onError={() => setFailed(true)} />;
}
