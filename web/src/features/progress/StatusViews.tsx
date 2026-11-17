// Estados comuns das telas da trilha: carregando e erro com "tentar de novo".
export function LoadingView({ label }: { label: string }) {
  return (
    <p className="status" role="status">
      {label}
    </p>
  );
}

export function ErrorView({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="status" role="alert">
      <p className="error">{message}</p>
      <p className="muted">Confira se a API (ou o mock) está rodando na porta 8000.</p>
      <button type="button" onClick={onRetry}>
        Tentar de novo
      </button>
    </div>
  );
}
