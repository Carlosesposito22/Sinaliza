import { FormEvent, useEffect, useState } from "react";
import { fetchCategories, fetchVocabulary, translate, type Category, type TranslateResponse, type WordMatch } from "./api";
import { Avatar } from "./Avatar";

function MatchWord({ match }: { match: WordMatch }) {
  if (match.kind === "function") {
    return <span className="word function">{match.word}</span>;
  }
  if (match.kind === "ignored") {
    return (
      <span className="word ignored" title="sem sinal no vocabulário">
        {match.word}
      </span>
    );
  }
  const title =
    match.kind === "approx"
      ? `aproximada por similaridade (${Math.round(match.score * 100)}%): confira se o sinal serve`
      : undefined;
  return (
    <span className={`word ${match.kind}`} title={title}>
      <span className="source">{match.word}</span>
      <span className="gloss">
        {match.kind === "approx" ? "~ " : ""}
        {match.gloss}
      </span>
    </span>
  );
}

export function App() {
  const [text, setText] = useState("O filho está com dor de cabeça.");
  const [result, setResult] = useState<TranslateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [signCount, setSignCount] = useState<number | null>(null);

  useEffect(() => {
    fetchCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
    fetchVocabulary()
      .then((signs) => setSignCount(signs.length))
      .catch(() => setSignCount(null));
  }, []);

  const run = async (value: string) => {
    setLoading(true);
    setError(null);
    try {
      setResult(await translate(value));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    void run(text);
  };

  const pickPhrase = (phrase: string) => {
    setText(phrase);
    void run(phrase);
  };

  const category = categories.find((c) => c.id === categoryId);
  const hasApprox = result?.matches.some((m) => m.kind === "approx") ?? false;
  const hasIgnored = result?.matches.some((m) => m.kind === "ignored") ?? false;

  return (
    <main className="app">
      <h1>Sinaliza</h1>
      <p className="subtitle">
        Digite um texto e veja a sequência de sinais, na ordem do texto. O vocabulário tem{" "}
        {signCount ?? "poucos"} sinais e isto não é uma tradução para Libras.
      </p>

      {categories.length > 0 && (
        <section className="categories" aria-label="Frases de exemplo por categoria">
          <p className="label">Frases de exemplo</p>
          <div className="chips">
            {categories.map((c) => (
              <button
                key={c.id}
                type="button"
                className="chip"
                aria-pressed={c.id === categoryId}
                onClick={() => setCategoryId(c.id === categoryId ? null : c.id)}
              >
                {c.label}
              </button>
            ))}
          </div>
          {category && (
            <ul className="phrases">
              {category.phrases.map((p) => (
                <li key={p.text}>
                  <button type="button" className="phrase" onClick={() => pickPhrase(p.text)}>
                    {p.text}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <form onSubmit={onSubmit}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          rows={3}
          aria-label="Texto em português"
        />
        <button type="submit" disabled={loading || !text.trim()}>
          {loading ? "Gerando..." : "Traduzir"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <section className="result" aria-label="Palavras e sinais">
          <p className="words">
            {result.matches.map((m, i) => (
              <MatchWord key={`${m.word}-${i}`} match={m} />
            ))}
          </p>
          <p className="glosses">{result.glosses.join(" · ")}</p>
          {hasApprox && (
            <p className="note">
              Palavras com “~” foram aproximadas por similaridade com um sinal do vocabulário. É uma proposta: confira
              se o sinal serve.
            </p>
          )}
          {hasIgnored && <p className="note">Palavras riscadas não têm sinal no vocabulário e foram ignoradas.</p>}
        </section>
      )}

      <Avatar pose={result?.pose ?? null} />
    </main>
  );
}
