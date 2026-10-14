import { FormEvent, useState } from "react";
import { translate, type TranslateResponse } from "./api";
import { Avatar } from "./Avatar";

export function App() {
  const [text, setText] = useState("Olá, tudo bem?");
  const [result, setResult] = useState<TranslateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      setResult(await translate(text));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro desconhecido");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app">
      <h1>Sinaliza</h1>
      <p className="subtitle">Digite um texto e veja o avatar sinalizar em Libras.</p>

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
      {result && <p className="glosses">{result.glosses.join(" · ")}</p>}

      <Avatar pose={result?.pose ?? null} />
    </main>
  );
}
