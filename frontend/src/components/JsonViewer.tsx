import { useMemo, useState, type ReactNode } from "react";

type Props = {
  value: unknown;
  label?: string;
};

export function JsonViewer({ value, label = "JSON" }: Props) {
  const [expanded, setExpanded] = useState(true);
  const text = useMemo(() => JSON.stringify(value, null, 2), [value]);
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      // ignore clipboard failures
    }
  }

  return (
    <div className="json-viewer">
      <div className="json-toolbar">
        <span className="meta-label">{label}</span>
        <div className="json-actions">
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setExpanded((v) => !v)}>
            {expanded ? "Collapse" : "Expand"}
          </button>
          <button type="button" className="btn btn-ghost btn-sm" onClick={copy}>
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
      {expanded ? (
        <pre className="json-surface" tabIndex={0}>
          <code>{colorize(text)}</code>
        </pre>
      ) : (
        <p className="muted mono">
          {text.slice(0, 96)}
          {text.length > 96 ? "…" : ""}
        </p>
      )}
    </div>
  );
}

function colorize(raw: string): ReactNode[] {
  const regex =
    /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/g;
  const nodes: ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  let i = 0;
  while ((match = regex.exec(raw)) !== null) {
    if (match.index > last) {
      nodes.push(<span key={`t${i++}`}>{raw.slice(last, match.index)}</span>);
    }
    if (match[1] != null) {
      const cls = match[2] ? "json-key" : "json-string";
      nodes.push(
        <span key={`s${i++}`} className={cls}>
          {match[1]}
          {match[2] || ""}
        </span>,
      );
    } else if (match[3] != null) {
      nodes.push(
        <span key={`l${i++}`} className="json-literal">
          {match[3]}
        </span>,
      );
    } else {
      nodes.push(
        <span key={`n${i++}`} className="json-number">
          {match[0]}
        </span>,
      );
    }
    last = regex.lastIndex;
  }
  if (last < raw.length) {
    nodes.push(<span key={`t${i++}`}>{raw.slice(last)}</span>);
  }
  return nodes;
}
