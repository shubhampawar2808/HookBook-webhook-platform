type Props = {
  page: number;
  totalPages: number;
  total: number;
  onChange: (page: number) => void;
};

export function Pagination({ page, totalPages, total, onChange }: Props) {
  if (totalPages <= 1) {
    return (
      <div className="pagination meta-only">
        <span className="mono muted">{total} total</span>
      </div>
    );
  }
  return (
    <div className="pagination">
      <span className="mono muted">
        Page {page} / {totalPages} · {total} total
      </span>
      <div className="pagination-actions">
        <button
          type="button"
          className="btn btn-ghost"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
        >
          Previous
        </button>
        <button
          type="button"
          className="btn btn-ghost"
          disabled={page >= totalPages}
          onClick={() => onChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
