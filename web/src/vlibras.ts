// Player do VLibras (avatares Ícaro, Hosana e Guga): o Unity WebGL do widget vlibras-web-browsers (LGPL-3.0, versão de
// 2026-09-29), servido localmente de public/vlibras/. Os sinais também são locais (public/vlibras/signs/BR/, baixados
// por `npm run signs`); nada é buscado nos servidores do VLibras durante o uso.
// O tradutor de texto do VLibras não é usado: tocamos as nossas glosas.
import glossTable from "./vlibras-glosses.json";

const TARGET = "vlibras";
const signsUrl = () => `${window.location.origin}/${TARGET}/signs/BR/`;

export type VlibrasAvatarName = "icaro" | "hosana" | "guga";

const SPLIT: Record<string, string[]> = glossTable.split;

// No dicionário do VLibras, sinal de várias palavras usa "_" (CADEIRA_DE_RODAS).
export function toVlibrasGloss(glosses: string[]): string {
  return glosses.flatMap((g) => SPLIT[g] ?? [g.replace(/ /g, "_")]).join(" ");
}

interface UnityInstance {
  SendMessage(object: string, method: string, value?: string | number): void;
}

declare global {
  interface Window {
    UnityLoader?: { instantiate(container: HTMLElement, setup: string, options?: object): UnityInstance };
    onLoadPlayer?: () => void;
    onPlayingStateChange?: (playing: string, paused: string, interval: string, loading: string) => void;
    CounterGloss?: (counter: number, total: number) => void;
    updateProgress?: (progress: number) => void;
    GetAvatar?: () => void;
    FinishWelcome?: () => void;
  }
}

export interface PlayerState {
  loaded: boolean;
  playing: boolean;
  loading: boolean;
}

type Listener = (state: PlayerState) => void;

// O Unity só pode ser instanciado uma vez por página: o player é um singleton e o elemento dele
// é movido para o contêiner do componente que estiver montado.
class VlibrasPlayer {
  readonly element: HTMLDivElement;
  private unity: UnityInstance | null = null;
  private state: PlayerState = { loaded: false, playing: false, loading: false };
  private pending: string | null = null;
  private listeners = new Set<Listener>();
  private started = false;
  private subtitles = true;
  private speed = 1;
  private restoreSpeedAfterPlay = false;

  constructor() {
    this.element = document.createElement("div");
    this.element.id = "vlibras-player";
    this.element.className = "vlibras-player";
  }

  start(): void {
    if (this.started) return;
    this.started = true;
    window.onLoadPlayer = () => {
      this.send("setBaseUrl", signsUrl());
      this.send("initRandomAnimationsProcess");
      this.send("setSubtitlesState", this.subtitles ? 1 : 0);
      this.send("setSlider", this.speed);
      this.set({ loaded: true });
      if (this.pending) this.play(this.pending);
    };
    window.onPlayingStateChange = (playing, paused, _interval, loading) => {
      const nowPlaying = playing !== "False" && paused === "False";
      // Terminou uma reprodução em câmera lenta: volta para a velocidade escolhida.
      if (this.state.playing && !nowPlaying && this.restoreSpeedAfterPlay) {
        this.restoreSpeedAfterPlay = false;
        this.send("setSlider", this.speed);
      }
      this.set({ playing: nowPlaying, loading: loading !== "False" });
    };
    window.CounterGloss = () => {};
    window.updateProgress = () => {};
    window.GetAvatar = () => {};
    window.FinishWelcome = () => {};

    const script = document.createElement("script");
    script.src = `${TARGET}/unity-loader.js`;
    script.onload = () => {
      this.unity = window.UnityLoader!.instantiate(this.element, `${TARGET}/playerweb.json`);
    };
    document.body.appendChild(script);
  }

  play(gloss: string): void {
    this.pending = gloss;
    if (!this.state.loaded) return;
    this.send("playNow", gloss);
  }

  setAvatar(name: VlibrasAvatarName): void {
    this.send("Change", name);
  }

  // Velocidade de reprodução (1 = normal, 0.5 = metade). Vale também se chamado antes de o player carregar.
  setSpeed(speed: number): void {
    this.speed = speed;
    this.restoreSpeedAfterPlay = false;
    if (this.state.loaded) this.send("setSlider", speed);
  }

  // Toca uma vez numa velocidade e depois volta para a escolhida (botão "câmera lenta").
  playAtSpeed(gloss: string, speed: number): void {
    if (!this.state.loaded) return;
    this.send("setSlider", speed);
    this.restoreSpeedAfterPlay = speed !== this.speed;
    this.play(gloss);
  }

  // Legenda do player (a glosa escrita embaixo do avatar). A prova do tema a desliga: lá a pessoa
  // precisa entender o sinal sem ler a resposta. Vale também se chamado antes de o player carregar.
  setSubtitles(enabled: boolean): void {
    this.subtitles = enabled;
    if (this.state.loaded) this.send("setSubtitlesState", enabled ? 1 : 0);
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    listener(this.state);
    return () => this.listeners.delete(listener);
  }

  private send(method: string, value?: string | number): void {
    this.unity?.SendMessage("PlayerManager", method, value);
  }

  private set(change: Partial<PlayerState>): void {
    this.state = { ...this.state, ...change };
    this.listeners.forEach((l) => l(this.state));
  }
}

let player: VlibrasPlayer | null = null;

export function vlibrasPlayer(): VlibrasPlayer {
  player ??= new VlibrasPlayer();
  return player;
}
