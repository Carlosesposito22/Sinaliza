import { useEffect, useState } from "react";
import { fetchPath } from "../learnApi";

export function AboutPage() {
  const [disclaimer, setDisclaimer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPath()
      .then((p) => setDisclaimer(p.disclaimer))
      .catch((e) => setError(e instanceof Error ? e.message : "Erro desconhecido"));
  }, []);

  return (
    <main className="status">
      <h1>Sobre</h1>
      {error && <p className="error">{error}</p>}
      {disclaimer && <p>{disclaimer}</p>}
      <p>Isto é uma sequência de sinais, não uma tradução para Libras.</p>
      <p>Créditos: avatar e sinais do VLibras; vocabulário do V-LIBRASIL; corpus VLibrasBD. Detalhes em docs/creditos-e-licencas.md.</p>
    </main>
  );
}
