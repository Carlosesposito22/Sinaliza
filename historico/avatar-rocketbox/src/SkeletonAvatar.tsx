import { useEffect, useRef } from "react";
import * as THREE from "three";
import type { PoseSequence } from "./api";
import { BONES, NUM_KEYPOINTS } from "./skeleton";

// Ponto não detectado vem como [0, 0, 0]; sai de cena em vez de aparecer na origem.
const OFFSCREEN = [0, 0, -1000];
const isMissing = (p: number[]) => p[0] === 0 && p[1] === 0 && p[2] === 0;

interface AvatarProps {
  pose: PoseSequence | null;
}

// Avatar em esqueleto (reserva, se o modelo 3D não carregar): desenha os keypoints e os ossos. Para um avatar com rig,
// substituir este componente mantendo a mesma entrada (PoseSequence).
export function SkeletonAvatar({ pose }: AvatarProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const poseRef = useRef<PoseSequence | null>(pose);
  const startRef = useRef(0);

  useEffect(() => {
    poseRef.current = pose;
    startRef.current = performance.now();
  }, [pose]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.set(0, -0.45, 5.5);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    mount.appendChild(renderer.domElement);

    const jointPositions = new Float32Array(NUM_KEYPOINTS * 3);
    const jointGeometry = new THREE.BufferGeometry();
    jointGeometry.setAttribute("position", new THREE.BufferAttribute(jointPositions, 3));
    const joints = new THREE.Points(
      jointGeometry,
      new THREE.PointsMaterial({ color: 0x2563eb, size: 0.07 }),
    );
    joints.frustumCulled = false;
    scene.add(joints);

    const bonePositions = new Float32Array(BONES.length * 2 * 3);
    const boneGeometry = new THREE.BufferGeometry();
    boneGeometry.setAttribute("position", new THREE.BufferAttribute(bonePositions, 3));
    const bones = new THREE.LineSegments(
      boneGeometry,
      new THREE.LineBasicMaterial({ color: 0x64748b }),
    );
    bones.frustumCulled = false;
    scene.add(bones);

    const resize = () => {
      const { clientWidth, clientHeight } = mount;
      renderer.setSize(clientWidth, clientHeight);
      camera.aspect = clientWidth / clientHeight;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();

    let raf = 0;
    const tick = () => {
      const current = poseRef.current;
      if (current && current.frames.length > 0) {
        const elapsed = (performance.now() - startRef.current) / 1000;
        const index = Math.floor(elapsed * current.fps) % current.frames.length;
        const frame = current.frames[index];
        for (let i = 0; i < NUM_KEYPOINTS; i++) {
          jointPositions.set(isMissing(frame[i]) ? OFFSCREEN : frame[i], i * 3);
        }
        BONES.forEach(([a, b], i) => {
          const hidden = isMissing(frame[a]) || isMissing(frame[b]);
          bonePositions.set(hidden ? OFFSCREEN : frame[a], i * 6);
          bonePositions.set(hidden ? OFFSCREEN : frame[b], i * 6 + 3);
        });
        jointGeometry.attributes.position.needsUpdate = true;
        boneGeometry.attributes.position.needsUpdate = true;
      }
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    tick();

    return () => {
      cancelAnimationFrame(raf);
      observer.disconnect();
      jointGeometry.dispose();
      boneGeometry.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return <div className="avatar" ref={mountRef} />;
}
