// Dicionário: os 210 sinais do nosso vocabulário curado (V-LIBRASIL), com os que a pessoa já viu nas aulas
// em destaque. Toque num sinal para vê-lo no avatar. Dados de GET /learn/dictionary; só front, não é ML.
import { useCallback, useEffect, useMemo, useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import type { DictionaryResponse } from "../../contract";
import { fetchDictionary } from "../../learnApi";
import { usePlayGlosses } from "../../app/AvatarContext";
import { useLearn } from "../progress/LearnContext";
import { ErrorView, LoadingView } from "../progress/StatusViews";
import { filterDictionary, initial, type DictionaryFilter } from "./dictionary";

export function DictionaryPage() {
  const { path, progress } = useLearn();
  const play = usePlayGlosses();
  const [data, setData] = useState<DictionaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<DictionaryFilter>("seen");
  const [query, setQuery] = useState("");
  const [current, setCurrent] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const body = await fetchDictionary();
      setData(body);
      if (body.seen_count === 0) setFilter("all");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível carregar o dicionário.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, progress]);

  const visible = useMemo(() => (data ? filterDictionary(data.signs, filter, query) : []), [data, filter, query]);
  const themeTitle = (id: string) => path?.themes.find((t) => t.id === id)?.title ?? id;

  if (error && !data) return <ErrorView message={error} onRetry={() => void load()} />;
  if (!data) return <LoadingView label="Carregando o dicionário…" />;

  let lastInitial = "";
  return (
    <main className="dictionary">
      <h1>Dicionário</h1>
      <p className="muted">
        Os {data.total} sinais do nosso vocabulário. Você já viu {data.seen_count} nas aulas. Toque num sinal para vê-lo no
        avatar acima.
      </p>
      <div className="dictionary-tools">
        <div className="chips" role="group" aria-label="Quais sinais mostrar">
          <button type="button" className="chip" aria-pressed={filter === "seen"} onClick={() => setFilter("seen")}>
            Meus sinais ({data.seen_count})
          </button>
          <button type="button" className="chip" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>
            Todos ({data.total})
          </button>
        </div>
        <input
          type="search"
          className="ex-input dictionary-search"
          placeholder="Buscar palavra"
          aria-label="Buscar palavra"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {visible.length === 0 ? (
        <p className="status">
          {filter === "seen" && !query ? "Você ainda não viu nenhum sinal. Comece uma aula na trilha!" : "Nenhum sinal encontrado."}
        </p>
      ) : (
        <ul className="dictionary-list">
          {visible.map((s) => {
            const letter = initial(s.word);
            const header = letter !== lastInitial;
            lastInitial = letter;
            const others = s.forms.filter((f) => f !== s.word);
            return (
              <li key={s.gloss}>
                {header && (
                  <span className="dictionary-letter" aria-hidden="true">
                    {letter}
                  </span>
                )}
                <button
                  type="button"
                  className={current === s.gloss ? "dictionary-item playing" : "dictionary-item"}
                  onClick={() => {
                    setCurrent(s.gloss);
                    play([s.gloss]);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                  aria-label={`${s.word}: ver o sinal no avatar`}
                >
                  <span className="dictionary-word">
                    {s.word}
                    {others.length > 0 && <span className="muted"> · {others.join(", ")}</span>}
                  </span>
                  <span className="dictionary-tags">
                    {s.theme_ids.map((t) => (
                      <span key={t} className="tag">
                        {themeTitle(t)}
                      </span>
                    ))}
                    {!s.seen && s.theme_ids.length === 0 && <span className="tag muted">fora da trilha</span>}
                    {s.mistakes > 0 && (
                      <span className="tag tag-warn">
                        <RotateCcw size={12} aria-hidden="true" /> revisar
                      </span>
                    )}
                  </span>
                  <Play size={16} aria-hidden="true" className="dictionary-play" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
