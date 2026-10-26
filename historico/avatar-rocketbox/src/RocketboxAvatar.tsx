import { useEffect, useRef } from "react";
import * as THREE from "three";
import { FBXLoader } from "three/examples/jsm/loaders/FBXLoader.js";
import type { PoseSequence } from "./api";
import { NUM_KEYPOINTS } from "./skeleton";
import { idlePoints, Retargeter, samplePose } from "./retarget";
import { prepareMotion, sampleBody, type PreparedMotion } from "./motion";
import { rocketboxLookup } from "./rocketbox";

const BASE = `${import.meta.env.BASE_URL}avatar/`;
export const AVATAR_URL = `${BASE}avatar.fbx`;

// O FBX do Rocketbox aponta para texturas TGA em pastas do autor; as nossas ficam ao lado do modelo.
const TEXTURES: Record<string, { file: string; transparent?: boolean }> = {
  m014_body: { file: "body.jpg" },
  m014_head: { file: "head.jpg" },
  m014_opacity: { file: "opacity.webp", transparent: true },
};

const MODEL_SCALE = 0.01; // o modelo está em centímetros

// Constante de tempo (s) da suavização das rotações: igual em qualquer taxa de quadros do monitor.
const SMOOTHING_SECONDS = 0.02;
const IDLE_SMOOTHING_SECONDS = 0.1;

interface AvatarProps {
  pose: PoseSequence | null;
  onError?: (error: unknown) => void;
}

// Avatar 3D (Microsoft Rocketbox, FBX) animado pelos keypoints. Se o modelo não carregar,
// chama `onError` e quem usa troca pelo esqueleto.
export function RocketboxAvatar({ pose, onError }: AvatarProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const motionRef = useRef<PreparedMotion | null>(null);
  const startRef = useRef(0);
  const errorRef = useRef(onError);
  errorRef.current = onError;

  useEffect(() => {
    motionRef.current = pose && pose.frames.length > 0 ? prepareMotion(pose) : null;
    startRef.current = performance.now();
  }, [pose]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(26, 1, 0.1, 20);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    mount.appendChild(renderer.domElement);

    scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.4));
    const key = new THREE.DirectionalLight(0xffffff, 1.8);
    key.position.set(1.2, 2.2, 2.5);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x9db8ff, 0.8);
    rim.position.set(-2, 1.5, -1.5);
    scene.add(rim);

    let model: THREE.Group | null = null;
    let retargeter: Retargeter | null = null;
    let disposed = false;
    const textures: THREE.Texture[] = [];
    const buffer = new Float32Array(NUM_KEYPOINTS * 3);
    const bodyBuffer = new Float32Array(4);
    const idle = idlePoints();
    const clock = new THREE.Clock();

    const resize = () => {
      const { clientWidth, clientHeight } = mount;
      if (!clientWidth || !clientHeight) return;
      renderer.setSize(clientWidth, clientHeight);
      camera.aspect = clientWidth / clientHeight;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(mount);
    resize();

    // Texturas TGA que o FBX cita não existem aqui: um "carregador" vazio evita o aviso e a busca.
    const manager = new THREE.LoadingManager();
    manager.addHandler(/\.tga$/i, {
      setPath: () => undefined,
      load: () => new THREE.Texture(),
    } as unknown as THREE.Loader);
    const textureLoader = new THREE.TextureLoader();

    const applyMaterials = (mesh: THREE.Mesh) => {
      const list = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      const replaced = list.map((old) => {
        const spec = TEXTURES[old.name];
        const map = textureLoader.load(`${BASE}${spec?.file ?? "body.jpg"}`);
        map.colorSpace = THREE.SRGBColorSpace;
        map.anisotropy = renderer.capabilities.getMaxAnisotropy();
        textures.push(map);
        old.dispose();
        return new THREE.MeshStandardMaterial({
          name: old.name,
          map,
          roughness: 0.85,
          metalness: 0,
          // cabelo e cílios: o canal alfa da textura recorta a forma
          transparent: Boolean(spec?.transparent),
          alphaTest: spec?.transparent ? 0.4 : 0,
          side: spec?.transparent ? THREE.DoubleSide : THREE.FrontSide,
        });
      });
      mesh.material = Array.isArray(mesh.material) ? replaced : replaced[0];
    };

    // Enquadra da cabeça à cintura, olhando de frente.
    const frame = (root: THREE.Object3D) => {
      root.updateMatrixWorld(true);
      const head = root.getObjectByName("Bip01_Head")?.getWorldPosition(new THREE.Vector3());
      const pelvis = root.getObjectByName("Bip01_Pelvis")?.getWorldPosition(new THREE.Vector3());
      if (!head || !pelvis) return;
      const top = head.y + 0.28;
      const bottom = pelvis.y - 0.05;
      const centerY = (top + bottom) / 2;
      const span = top - bottom;
      const distance = span / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
      camera.position.set(0, centerY, distance * 1.08);
      camera.lookAt(0, centerY, 0);
    };

    new FBXLoader(manager).load(
      AVATAR_URL,
      (loaded) => {
        if (disposed) return;
        // o FBX traz uma luz ambiente própria; as nossas bastam
        for (const light of loaded.children.filter((c) => (c as THREE.Light).isLight)) loaded.remove(light);
        loaded.scale.setScalar(MODEL_SCALE);
        loaded.traverse((object) => {
          object.frustumCulled = false;
          if ((object as THREE.Mesh).isMesh) applyMaterials(object as THREE.Mesh);
        });
        scene.add(loaded);
        loaded.updateMatrixWorld(true);
        model = loaded;
        retargeter = new Retargeter(loaded, rocketboxLookup(loaded));
        frame(loaded);
      },
      undefined,
      (error) => {
        if (!disposed) errorRef.current?.(error);
      },
    );

    let raf = 0;
    const tick = () => {
      const dt = Math.min(clock.getDelta(), 0.1);
      if (model && retargeter) {
        const motion = motionRef.current;
        if (motion) {
          const alpha = 1 - Math.exp(-dt / SMOOTHING_SECONDS);
          const elapsed = (performance.now() - startRef.current) / 1000;
          samplePose(motion.frames, motion.fps, elapsed, buffer);
          sampleBody(motion.body, motion.fps, elapsed, bodyBuffer);
          retargeter.applyBody(bodyBuffer, alpha);
          retargeter.apply(buffer, alpha);
        } else {
          const alpha = 1 - Math.exp(-dt / IDLE_SMOOTHING_SECONDS);
          retargeter.applyBody(null, alpha);
          retargeter.apply(idle, alpha);
        }
      }
      renderer.render(scene, camera);
      raf = requestAnimationFrame(tick);
    };
    tick();

    return () => {
      disposed = true;
      cancelAnimationFrame(raf);
      observer.disconnect();
      if (model) {
        scene.remove(model);
        model.traverse((object) => {
          const mesh = object as THREE.Mesh;
          if (!mesh.isMesh) return;
          mesh.geometry.dispose();
          for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) material.dispose();
        });
      }
      for (const texture of textures) texture.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, []);

  return <div className="avatar" ref={mountRef} />;
}
