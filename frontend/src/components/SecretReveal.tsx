import { useState } from "react";

type Props = {
  secret: string;
  label: string;
  warning?: string;
};

export function SecretReveal({ secret, label, warning }: Props) {
  const [visible, setVisible] = useState(true);
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(secret);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  }

  return (
    <div className="secret-reveal" role="status">
      <div className="secret-reveal-head">
        <strong>{label}</strong>
        <span className="muted">Shown once — copy and store securely</span>
      </div>
      {warning ? <p className="secret-warn">{warning}</p> : null}
      <div className="secret-row">
        <code className="mono">{visible ? secret : "•".repeat(Math.min(40, secret.length))}</code>
        <button type="button" className="btn btn-ghost btn-sm" onClick={() => setVisible((v) => !v)}>
          {visible ? "Hide" : "Show"}
        </button>
        <button type="button" className="btn btn-primary btn-sm" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
    </div>
  );
}
