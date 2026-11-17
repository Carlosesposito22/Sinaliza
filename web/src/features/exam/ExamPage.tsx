// Prova do tema: o avatar sinaliza sem legenda e a pessoa escreve, em português, o que entendeu.
// A API corrige (regra, não ML) e decide se o próximo tema abre ou se é preciso refazer as aulas.
import { useCallback, useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { Check, Lock, Minus, Play, RotateCcw, Trophy, X } from "lucide-react";
import type { Exam, ExamResult, QuestionResult } from "../../contract";
import { fetchExam, submitExam } from "../../learnApi";
import { vlibrasPlayer } from "../../vlibras";
import { useAvatar, usePlayGlosses } from "../../app/AvatarContext";
import { useLearn } from "../progress/LearnContext";
import { Badge } from "../achievements/Badge";
import { ErrorView, LoadingView } from "../progress/StatusViews";
import { examOpen, percent, themeSummary } from "../trail/trail";
import { answeredCount, questionLabel, resultHeadline, reviewOrder, toSubmit, verdict } from "./exam";

type Phase = "loading" | "intro" | "answering" | "submitting" | "result" | "error";

export function ExamPage() {
  const { themeId = "" } = useParams();
  const { path, progress, loading, error: learnError, reload, applyExamResult } = useLearn();
  const { setGlosses } = useAvatar();
  const [exam, setExam] = useState<Exam | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [index, setIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<ExamResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const theme = path?.themes.find((t) => t.id === themeId) ?? null;
  const open = examOpen(progress, themeId);

  const show = usePlayGlosses();

  const load = useCallback(async () => {
    setPhase("loading");
    setError(null);
    setResult(null);
    setAnswers({});
    setIndex(0);
    setGlosses([]);
    try {
      setExam(await fetchExam(themeId));
      setPhase("intro");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível abrir a prova.");
      setPhase("error");
    }
  }, [themeId, setGlosses]);

  useEffect(() => {
    if (progress && open) void load();
  }, [progress === null, open, load]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sem legenda enquanto a prova corre; com legenda de volta na correção e ao sair da tela.
  useEffect(() => {
    vlibrasPlayer().setSubtitles(phase === "result");
  }, [phase]);
  useEffect(
    () => () => {
      vlibrasPlayer().setSubtitles(true);
      setGlosses([]);
    },
    [setGlosses],
  );

  const question = exam?.questions[index] ?? null;
  useEffect(() => {
    if (phase === "answering" && question) setGlosses(question.glosses);
  }, [phase, question, setGlosses]);

  if (learnError && !progress) return <ErrorView message={learnError} onRetry={() => void reload()} />;
  if (loading && (!path || !progress)) return <LoadingView label="Carregando a prova…" />;
  if (!path || !progress) return null;
  if (!theme) return <ClosedView title="Tema não encontrado." detail="Volte à trilha e escolha um tema." />;
  if (!open && phase !== "result") {
    const s = themeSummary(theme, progress);
    return (
      <ClosedView
        title={`A prova de ${theme.title} ainda está fechada.`}
        detail={
          s.status === "locked"
            ? "Passe na prova do tema anterior para abrir este tema."
            : `Conclua as aulas do tema primeiro (${s.completed} de ${s.total} feitas).`
        }
      />
    );
  }
  if (phase === "loading") return <LoadingView label="Preparando a prova…" />;
  if (phase === "error" || !exam) return <ErrorView message={error ?? "Erro desconhecido."} onRetry={() => void load()} />;

  if (phase === "intro") {
    return (
      <main className="exam" style={{ "--theme": theme.color } as CSSProperties}>
        <p className="exam-kicker">
          <Trophy size={16} aria-hidden="true" /> Prova do tema
          <Link to="/trilha" className="exam-exit">
            <X size={16} aria-hidden="true" /> Sair
          </Link>
        </p>
        <h1>{theme.title}</h1>
        <ul className="exam-rules">
          <li>O avatar vai sinalizar {exam.questions.length} sinais e frases, <strong>sem legenda</strong>.</li>
          <li>Escreva em português o que você entendeu. Pode repetir o sinal quantas vezes quiser.</li>
          <li>
            Nota mínima: <strong>{percent(exam.pass_score)}%</strong>. Passando, o próximo tema abre. Se não passar, você
            refaz as aulas do tema e tenta de novo.
          </li>
          <li>Maiúsculas, acentos e a ordem das palavras não contam. Nas frases, cada sinal certo vale nota.</li>
        </ul>
        <p className="disclaimer">{path.disclaimer}</p>
        <button type="button" className="btn btn-primary" onClick={() => setPhase("answering")}>
          Começar a prova
        </button>
      </main>
    );
  }

  if ((phase === "answering" || phase === "submitting") && question) {
    const last = index === exam.questions.length - 1;
    const value = answers[question.id] ?? "";
    const blank = exam.questions.length - answeredCount(exam, answers);
    const submit = async () => {
      setPhase("submitting");
      try {
        const graded = await submitExam(themeId, toSubmit(exam, answers));
        applyExamResult(graded);
        setResult(graded);
        setGlosses([]);
        setPhase("result");
        window.scrollTo({ top: 0 });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Não foi possível enviar a prova.");
        setPhase("answering");
      }
    };
    const onSubmit = (event: FormEvent) => {
      event.preventDefault();
      if (phase === "submitting") return;
      if (last) void submit();
      else setIndex(index + 1);
    };
    return (
      <main className="exam" style={{ "--theme": theme.color } as CSSProperties}>
        <div className="exam-progress">
          <span className="exam-progress-row">
            Questão {index + 1} de {exam.questions.length}
            <Link to="/trilha" className="exam-exit" aria-label="Sair da prova (as respostas não são salvas)">
              <X size={16} aria-hidden="true" /> Sair
            </Link>
          </span>
          <div className="bar" role="progressbar" aria-label="Progresso da prova" aria-valuemin={0} aria-valuemax={exam.questions.length} aria-valuenow={index + 1}>
            <div className="bar-fill" style={{ width: `${((index + 1) / exam.questions.length) * 100}%` }} />
          </div>
        </div>
        <form className="exam-form" onSubmit={onSubmit}>
          <label htmlFor="exam-answer" className="exam-question">
            {questionLabel(question.kind, question.glosses.length)}
          </label>
          <input
            id="exam-answer"
            key={question.id}
            autoFocus
            autoComplete="off"
            autoCapitalize="off"
            spellCheck={false}
            maxLength={300}
            value={value}
            placeholder="Escreva em português o que o avatar sinalizou"
            onChange={(e) => setAnswers({ ...answers, [question.id]: e.target.value })}
          />
          {error && <p className="error">{error}</p>}
          {last && blank > 0 && (
            <p className="muted">
              {blank === 1 ? "1 questão está em branco e vai valer 0." : `${blank} questões estão em branco e vão valer 0.`}
            </p>
          )}
          <div className="exam-actions">
            <button type="button" className="btn btn-secondary" disabled={index === 0 || phase === "submitting"} onClick={() => setIndex(index - 1)}>
              Voltar
            </button>
            <button type="submit" className="btn btn-primary" disabled={phase === "submitting"}>
              {phase === "submitting" ? "Corrigindo…" : last ? "Entregar prova" : value.trim() ? "Próxima" : "Pular"}
            </button>
          </div>
        </form>
      </main>
    );
  }

  if (phase === "result" && result) {
    const mustRedo = result.must_redo_lesson_ids.length;
    const unlocked = path.themes.filter((t) => result.unlocked_theme_ids.includes(t.id)).map((t) => t.title);
    return (
      <main className="exam" style={{ "--theme": theme.color } as CSSProperties}>
        <section className={`exam-score-card ${result.passed ? "passed" : "failed"}`} aria-live="polite">
          <p className="exam-score">{percent(result.score)}%</p>
          <h1>{resultHeadline(result)}</h1>
          <p>
            Nota mínima: {percent(result.pass_score)}%.
            {result.xp_gained > 0 && ` +${result.xp_gained} XP.`}
            {unlocked.length > 0 && ` Tema liberado: ${unlocked.join(", ")}.`}
          </p>
          {result.new_achievements.length > 0 && (
            <ul className="exam-achievements" aria-label="Conquistas ganhas nesta prova">
              {result.new_achievements.map((a) => (
                <li key={a.id}>
                  <Badge achievement={a} size="sm" /> {a.title}
                </li>
              ))}
            </ul>
          )}
          {!result.passed && mustRedo > 0 && (
            <p>
              Para tentar de novo, refaça as {mustRedo} aulas de {theme.title}. Elas estão marcadas na trilha com{" "}
              <RotateCcw size={14} aria-label="refazer" />.
            </p>
          )}
          <div className="exam-actions">
            {result.passed || mustRedo > 0 ? (
              <Link to="/trilha" className="btn btn-primary">
                {result.passed ? "Voltar à trilha" : "Refazer as aulas"}
              </Link>
            ) : (
              <button type="button" className="btn btn-primary" onClick={() => void load()}>
                Fazer a prova de novo
              </button>
            )}
          </div>
        </section>

        <h2 className="exam-review-title">Correção</h2>
        <p className="muted">Toque em “Ver o sinal” para rever no avatar (agora com legenda).</p>
        <ol className="exam-review">
          {reviewOrder(result.questions).map((q) => (
            <ReviewItem key={q.question_id} q={q} onShow={() => show(q.glosses)} />
          ))}
        </ol>
      </main>
    );
  }

  return null;
}

function ReviewItem({ q, onShow }: { q: QuestionResult; onShow: () => void }) {
  const v = verdict(q);
  const Icon = v === "right" ? Check : v === "partial" ? Minus : X;
  return (
    <li className={`review-item ${v}`}>
      <div className="review-head">
        <Icon size={18} aria-hidden="true" className="review-icon" />
        <strong>{q.expected_text}</strong>
        <span className="review-score">{percent(q.score)}%</span>
      </div>
      <p className="muted">
        Você escreveu: {q.answer ? <q>{q.answer}</q> : <em>(em branco)</em>}
      </p>
      <ul className="review-signs" aria-label="Sinais">
        {q.signs.map((s, i) => (
          <li key={`${s.gloss}-${i}`} className={s.correct ? "ok" : "miss"}>
            {s.correct ? "✓" : "✗"} {s.word}
          </li>
        ))}
        {q.extra_words.map((w, i) => (
          <li key={`extra-${w}-${i}`} className="extra" title="palavra que não corresponde a nenhum sinal">
            + {w}
          </li>
        ))}
      </ul>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onShow}>
        <Play size={14} aria-hidden="true" /> Ver o sinal
      </button>
    </li>
  );
}

function ClosedView({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="status">
      <p>
        <Lock size={16} aria-hidden="true" /> {title}
      </p>
      <p className="muted">{detail}</p>
      <Link to="/trilha">Voltar à trilha</Link>
    </div>
  );
}
