type Props = {
  title?: string;
  message: string;
  onRetry?: () => void;
};

export function ErrorMessage({ title = "Something went wrong", message, onRetry }: Props) {
  return (
    <div className="error-panel" role="alert">
      <div>
        <strong>{title}</strong>
        <p>{message}</p>
      </div>
      {onRetry ? (
        <button type="button" className="btn btn-ghost" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}
