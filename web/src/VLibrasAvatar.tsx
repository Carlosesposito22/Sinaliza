import { useEffect, useRef, useState } from "react";
import { toVlibrasGloss, vlibrasPlayer, type PlayerState, type VlibrasAvatarName } from "./vlibras";

const AVATARS: { name: VlibrasAvatarName; label: string }[] = [
  { name: "icaro", label: "Ícaro" },
  { name: "hosana", label: "Hosana" },
  { name: "guga", label: "Guga" },
];

// Velocidades oferecidas. "Devagar" ajuda quem está aprendendo a ver a configuração de mão.
const SPEEDS = [
  { value: 0.5, label: "Devagar" },
  { value: 1, label: "Normal" },
];
// O player não vai abaixo de metade da velocidade (medido: 0,35 e 0,5 dão o mesmo tempo).
const SLOW_MOTION = 0.5;
const SPEED_KEY = "sinaliza.avatarSpeed";

function savedSpeed(): number {
  try {
    const value = Number(localStorage.getItem(SPEED_KEY));
    return SPEEDS.some((s) => s.value === value) ? value : 1;
  } catch {
    return 1; // localStorage indisponível: velocidade normal
  }
}

interface VLibrasAvatarProps {
  glosses: string[];
}

// Avatar do VLibras tocando as nossas glosas (do vocabulário curado) com os sinais servidos localmente.
export function VLibrasAvatar({ glosses }: VLibrasAvatarProps) {
  const container = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<PlayerState>({ loaded: false, playing: false, loading: false });
  const [avatar, setAvatar] = useState<VlibrasAvatarName>("icaro");
  const [speed, setSpeed] = useState<number>(savedSpeed);
  const gloss = toVlibrasGloss(glosses);

  useEffect(() => {
    const player = vlibrasPlayer();
    container.current?.appendChild(player.element);
    player.start();
    return player.subscribe(setState);
  }, []);

  useEffect(() => {
    vlibrasPlayer().setSpeed(speed);
    try {
      localStorage.setItem(SPEED_KEY, String(speed));
    } catch {
      // sem localStorage: a escolha vale só nesta visita
    }
  }, [speed]);

  useEffect(() => {
    if (gloss) vlibrasPlayer().play(gloss);
  }, [gloss]);

  const pickAvatar = (name: VlibrasAvatarName) => {
    setAvatar(name);
    vlibrasPlayer().setAvatar(name);
  };

  return (
    <>
      <div className="avatar-toolbar">
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
        <div className="chips avatar-kind avatar-speed" role="group" aria-label="Velocidade do avatar">
          {SPEEDS.map((s) => (
            <button key={s.value} type="button" className="chip" aria-pressed={s.value === speed} onClick={() => setSpeed(s.value)}>
              {s.label}
            </button>
          ))}
        </div>
      </div>
      <div className="avatar vlibras" ref={container}>
        {!state.loaded && <p className="avatar-status">Carregando o avatar…</p>}
        {state.loaded && gloss && (
          <div className="replay">
            {speed > SLOW_MOTION && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => vlibrasPlayer().playAtSpeed(gloss, SLOW_MOTION)}
                disabled={state.playing}
                title="Toca uma vez devagar e volta à velocidade normal"
              >
                Câmera lenta
              </button>
            )}
            <button type="button" onClick={() => vlibrasPlayer().play(gloss)} disabled={state.playing}>
              Repetir
            </button>
          </div>
        )}
      </div>
    </>
  );
}
