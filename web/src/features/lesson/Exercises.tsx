// Um componente por tipo de exercício. Só front; não é ML. A nota de cada exercício sai daqui por
// `onAnswer(correto, detalhe)`; o detalhe (a resposta certa) aparece na barra de feedback.
// Regra de conteúdo: o nome do sinal (glosa) nunca aparece antes da resposta, porque ele entrega a palavra.
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import type { CheckResult } from "../../contract";
import { checkAnswer } from "../../learnApi";
import { usePlayGlosses } from "../../app/AvatarContext";
import type { KnownExercise, LearnPhrase, LearnSign, MatchPairs, PhraseToText, SignToText, SignToWord, WordToSign } from "./exerciceTypes";
import { gradeChoice, gradeMatchPairs, isPairMatch } from "./grading";

export interface ExerciseProps<T> {
  exercise: T;
  locked: boolean; // já respondeu: só falta "Continuar"
  onAnswer: (correct: boolean, detail?: ReactNode) => void;
  onAcknowledge: () => void;
}

// Toca a sequência quando o exercício abre (e de novo se for o mesmo sinal do anterior).
function useAutoPlay(id: string, glosses: string[] | null) {
  const play = usePlayGlosses();
  useEffect(() => {
    if (glosses?.length) play(glosses);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
}

export function ExerciseView({ exercise, ...rest }: ExerciseProps<KnownExercise>) {
  switch (exercise.type) {
    case "learn_sign":
      return <IntroSign exercise={exercise} {...rest} />;
    case "learn_phrase":
      return <IntroPhrase exercise={exercise} {...rest} />;
    case "sign_to_word":
    case "phrase_to_text":
      return <ChoiceExercise exercise={exercise} {...rest} />;
    case "word_to_sign":
      return <WordToSignExercise exercise={exercise} {...rest} />;
    case "match_pairs":
      return <MatchPairsExercise exercise={exercise} {...rest} />;
    case "sign_to_text":
      return <WriteExercise exercise={exercise} {...rest} />;
  }
}

function IntroSign({ exercise, onAcknowledge }: ExerciseProps<LearnSign>) {
  useAutoPlay(exercise.id, [exercise.gloss]);
  const others = exercise.forms.filter((f) => f !== exercise.word_pt);
  return (
    <div className="ex ex-intro">
      <p className="ex-kicker">Sinal novo</p>
      <p className="ex-word">{exercise.word_pt}</p>
      {others.length > 0 && <p className="muted">Também vale: {others.join(", ")}</p>}
      <button type="button" className="btn btn-primary" onClick={onAcknowledge} autoFocus>
        Continuar
      </button>
    </div>
  );
}

function IntroPhrase({ exercise, onAcknowledge }: ExerciseProps<LearnPhrase>) {
  useAutoPlay(exercise.id, exercise.glosses);
  return (
    <div className="ex ex-intro">
      <p className="ex-kicker">Frase nova</p>
      <p className="ex-word ex-phrase">{exercise.text}</p>
      <ol className="ex-sequence" aria-label="Sinais em sequência">
        {exercise.glosses.map((g, i) => (
          <li key={`${g}-${i}`}>{g}</li>
        ))}
      </ol>
      <p className="muted small-note">Sequência de sinais na ordem do português; não é a gramática da Libras.</p>
      <button type="button" className="btn btn-primary" onClick={onAcknowledge} autoFocus>
        Continuar
      </button>
    </div>
  );
}

function ChoiceExercise({ exercise, locked, onAnswer }: ExerciseProps<SignToWord | PhraseToText>) {
  const glosses = exercise.type === "sign_to_word" ? [exercise.gloss] : exercise.glosses;
  useAutoPlay(exercise.id, glosses);
  const [picked, setPicked] = useState<string | null>(null);
  const correct = exercise.options.find((o) => o.id === exercise.correct_option_id);
  const verify = () => {
    if (!picked) return;
    onAnswer(gradeChoice(exercise, picked), <>Resposta: <strong>{correct?.text}</strong></>);
  };
  return (
    <div className="ex">
      <p className="ex-prompt">{exercise.type === "sign_to_word" ? "Que palavra é este sinal?" : "Que frase é esta?"}</p>
      <div className="ex-options" role="radiogroup">
        {exercise.options.map((o) => (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={picked === o.id}
            className={optionClass(locked, picked === o.id, o.id === exercise.correct_option_id)}
            disabled={locked}
            onClick={() => setPicked(o.id)}
          >
            {o.text}
          </button>
        ))}
      </div>
      {!locked && (
        <button type="button" className="btn btn-primary" disabled={!picked} onClick={verify}>
          Verificar
        </button>
      )}
    </div>
  );
}

function WordToSignExercise({ exercise, locked, onAnswer }: ExerciseProps<WordToSign>) {
  const play = usePlayGlosses();
  const [picked, setPicked] = useState<string | null>(null);
  const correctIndex = exercise.options.findIndex((o) => o.id === exercise.correct_option_id);
  const pick = (id: string, gloss: string) => {
    setPicked(id);
    play([gloss]);
  };
  return (
    <div className="ex">
      <p className="ex-prompt">
        Qual destes é o sinal de <strong>“{exercise.text}”</strong>?
      </p>
      <p className="muted">Toque em cada opção para ver o sinal no avatar.</p>
      <div className="ex-options ex-options-row" role="radiogroup">
        {exercise.options.map((o, i) => (
          <button
            key={o.id}
            type="button"
            role="radio"
            aria-checked={picked === o.id}
            className={optionClass(locked, picked === o.id, o.id === exercise.correct_option_id)}
            onClick={() => (locked ? play([o.gloss]) : pick(o.id, o.gloss))}
          >
            Sinal {i + 1}
          </button>
        ))}
      </div>
      {!locked && (
        <button
          type="button"
          className="btn btn-primary"
          disabled={!picked}
          onClick={() => picked && onAnswer(gradeChoice(exercise, picked), <>Era o <strong>sinal {correctIndex + 1}</strong>.</>)}
        >
          Verificar
        </button>
      )}
    </div>
  );
}

function MatchPairsExercise({ exercise, locked, onAnswer }: ExerciseProps<MatchPairs>) {
  const play = usePlayGlosses();
  const [sign, setSign] = useState<string | null>(null);
  const [matched, setMatched] = useState<string[]>([]);
  const [wrong, setWrong] = useState(0);
  const [flash, setFlash] = useState<string | null>(null);
  // As palavras ficam em outra ordem que os sinais, para não casar pela posição.
  const [words] = useState(() => [...exercise.pairs].sort((a, b) => a.text.localeCompare(b.text, "pt-BR")));

  const tryWord = (wordPairId: string) => {
    if (!sign || locked) return;
    if (isPairMatch(sign, wordPairId)) {
      const next = [...matched, sign];
      setMatched(next);
      setSign(null);
      if (next.length === exercise.pairs.length) {
        onAnswer(gradeMatchPairs(wrong), wrong ? <>Você ligou tudo, com {wrong} {wrong === 1 ? "erro" : "erros"} no caminho.</> : undefined);
      }
    } else {
      setWrong(wrong + 1);
      setFlash(wordPairId);
      window.setTimeout(() => setFlash(null), 600);
    }
  };

  return (
    <div className="ex">
      <p className="ex-prompt">Ligue cada sinal à sua palavra</p>
      <p className="muted">Toque num sinal para vê-lo no avatar e depois na palavra certa.</p>
      <div className="ex-match">
        <div className="ex-options">
          {exercise.pairs.map((p, i) => (
            <button
              key={p.id}
              type="button"
              aria-pressed={sign === p.id}
              className={matched.includes(p.id) ? "ex-option right" : sign === p.id ? "ex-option picked" : "ex-option"}
              disabled={matched.includes(p.id) || locked}
              onClick={() => {
                setSign(p.id);
                play([p.gloss]);
              }}
            >
              Sinal {i + 1}
            </button>
          ))}
        </div>
        <div className="ex-options">
          {words.map((p) => (
            <button
              key={p.id}
              type="button"
              className={matched.includes(p.id) ? "ex-option right" : flash === p.id ? "ex-option wrong" : "ex-option"}
              disabled={matched.includes(p.id) || locked || !sign}
              onClick={() => tryWord(p.id)}
            >
              {p.text}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function WriteExercise({ exercise, locked, onAnswer }: ExerciseProps<SignToText>) {
  useAutoPlay(exercise.id, exercise.glosses);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const verify = async (event: FormEvent) => {
    event.preventDefault();
    if (busy || locked) return;
    setBusy(true);
    setError(null);
    try {
      const result = await checkAnswer({ glosses: exercise.glosses, text: exercise.text, answer });
      onAnswer(result.correct, <CheckDetail result={result} />);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível corrigir agora.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="ex" onSubmit={verify}>
      <label htmlFor={`write-${exercise.id}`} className="ex-prompt">
        {exercise.kind === "sign" ? "Escreva a palavra deste sinal" : `Escreva esta frase (${exercise.glosses.length} sinais)`}
      </label>
      <p className="muted">Treino para a prova: escreva em português o que o avatar sinalizou.</p>
      <input
        id={`write-${exercise.id}`}
        className="ex-input"
        autoFocus
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        maxLength={300}
        value={answer}
        disabled={locked}
        onChange={(e) => setAnswer(e.target.value)}
        placeholder="Sua resposta"
      />
      {error && <p className="error">{error}</p>}
      {!locked && (
        <button type="submit" className="btn btn-primary" disabled={busy || !answer.trim()}>
          {busy ? "Corrigindo…" : "Verificar"}
        </button>
      )}
    </form>
  );
}

function CheckDetail({ result }: { result: CheckResult }) {
  return (
    <>
      Resposta: <strong>{result.expected_text}</strong>
      {result.signs.length > 1 && (
        <span className="review-signs inline">
          {result.signs.map((s, i) => (
            <span key={`${s.gloss}-${i}`} className={s.correct ? "ok" : "miss"}>
              {s.correct ? "✓" : "✗"} {s.word}
            </span>
          ))}
        </span>
      )}
      {result.extra_words.length > 0 && <> · sobrou: {result.extra_words.join(", ")}</>}
    </>
  );
}

function optionClass(locked: boolean, picked: boolean, isCorrect: boolean): string {
  if (locked && isCorrect) return "ex-option right";
  if (locked && picked) return "ex-option wrong";
  return picked ? "ex-option picked" : "ex-option";
}
