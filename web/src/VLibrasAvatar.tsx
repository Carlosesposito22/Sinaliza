import { useEffect, useRef, useState } from "react";
import { toVlibrasGloss, vlibrasPlayer, type PlayerState, type VlibrasAvatarName } from "./vlibras";

const AVATARS: { name: VlibrasAvatarName; label: string }[] = [
  { name: "icaro", label: "Ícaro" },
  { name: "hosana", label: "Hosana" },
  { name: "guga", label: "Guga" },
];

interface VLibrasAvatarProps {
  glosses: string[];
}

// Avatar do VLibras tocando as nossas glosas com os sinais do dicionário do VLibras (servidos localmente).
export function VLibrasAvatar({ glosses }: VLibrasAvatarProps) {
  const container = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<PlayerState>({ loaded: false, playing: false, loading: false });
  const [avatar, setAvatar] = useState<VlibrasAvatarName>("icaro");
  const gloss = toVlibrasGloss(glosses);

  useEffect(() => {
    const player = vlibrasPlayer();
    container.current?.appendChild(player.element);
    player.start();
    return player.subscribe(setState);
  }, []);

  useEffect(() => {
    if (gloss) vlibrasPlayer().play(gloss);
  }, [gloss]);

  const pickAvatar = (name: VlibrasAvatarName) => {
    setAvatar(name);
    vlibrasPlayer().setAvatar(name);
  };

  return (
    <>
      <div className="chips avatar-kind" role="group" aria-label="Avatar">
        {AVATARS.map((a) => (
          <button
            key={a.name}
            type="button"
            className="chip"
            aria-pressed={a.name === avatar}
            disabled={!state.loaded}
            onClick={() => pickAvatar(a.name)}
          >
            {a.label}
          </button>
        ))}
      </div>
      <div className="avatar vlibras" ref={container}>
        {!state.loaded && <p className="avatar-status">Carregando o avatar…</p>}
        {state.loaded && gloss && (
          <button type="button" className="replay" onClick={() => vlibrasPlayer().play(gloss)} disabled={state.playing}>
            Repetir
          </button>
        )}
      </div>
    </>
  );
}
