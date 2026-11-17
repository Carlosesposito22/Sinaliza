import { useLearn } from "../features/progress/LearnContext";

// Texto de reserva caso a API esteja fora: o aviso precisa aparecer de qualquer jeito.
const FALLBACK_DISCLAIMER =
  "Sinais do vocabulário curado pela equipe a partir do dicionário do VLibras; os rótulos não foram " +
  "validados por falante de Libras. Isto é uma sequência de sinais, não uma aula de Libras.";

export function AboutPage() {
  const { path } = useLearn();
  return (
    <main className="status">
      <h1>Sobre</h1>
      <p>{path?.disclaimer ?? FALLBACK_DISCLAIMER}</p>
      <p>Isto é uma sequência de sinais, não uma tradução para Libras.</p>
      <p>Créditos: avatar e sinais do VLibras; vocabulário do V-LIBRASIL; corpus VLibrasBD. Detalhes em docs/creditos-e-licencas.md.</p>
    </main>
  );
}
