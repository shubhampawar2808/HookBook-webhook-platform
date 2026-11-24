type Props = {
  size?: number;
  className?: string;
  title?: string;
};

/** Original logomark: forged event nodes with directional delivery flow. */
export function HookForgeMark({ size = 28, className, title = "HookForge" }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      className={className}
      role="img"
      aria-label={title}
    >
      <rect width="40" height="40" rx="8" fill="#292D27" />
      <path
        d="M9 20h6.5L18 13.5 22.5 27 25.5 20H31"
        stroke="#D97745"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="hf-flow-path"
      />
      <circle cx="9" cy="20" r="3" fill="#B6C28A" />
      <circle cx="31" cy="20" r="3" fill="#E8E2D4" />
      <circle cx="18" cy="13.5" r="1.6" fill="#A8A49A" />
      <circle cx="22.5" cy="27" r="1.6" fill="#A8A49A" />
    </svg>
  );
}
