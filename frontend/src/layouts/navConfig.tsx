import type { ReactNode } from "react";

type NavItem = {
  to: string;
  label: string;
  icon: ReactNode;
};

function Ico({ d }: { d: string }) {
  return (
    <svg className="nav-ico" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path d={d} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export const NAV_ITEMS: NavItem[] = [
  {
    to: "/",
    label: "Overview",
    icon: <Ico d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z" />,
  },
  {
    to: "/events",
    label: "Events",
    icon: <Ico d="M5 12h4l2-5 3 10 2-5h3" />,
  },
  {
    to: "/deliveries",
    label: "Deliveries",
    icon: <Ico d="M4 7h16M4 12h10M4 17h7" />,
  },
  {
    to: "/endpoints",
    label: "Endpoints",
    icon: <Ico d="M8 12h8M7 8a3 3 0 1 0 0 8M17 8a3 3 0 1 1 0 8" />,
  },
  {
    to: "/event-types",
    label: "Event Types",
    icon: <Ico d="M7 7h10v10H7zM10 4v3M14 4v3M10 17v3M14 17v3" />,
  },
  {
    to: "/subscriptions",
    label: "Subscriptions",
    icon: <Ico d="M7 8h10M7 12h10M7 16h6M17 16l2 2 3-3" />,
  },
  {
    to: "/api-keys",
    label: "API Keys",
    icon: <Ico d="M8 12a4 4 0 1 0 3.9 4.8L15 14l2 2 2-2-2-2 2.2-2.2A4 4 0 0 0 8 12Z" />,
  },
  {
    to: "/dead-letter",
    label: "Dead Letter",
    icon: <Ico d="M12 8v5M12 16.5h.01M5.5 19h13l-1.5-11h-10L5.5 19Z" />,
  },
  {
    to: "/settings",
    label: "Settings",
    icon: <Ico d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7ZM4 12h2M18 12h2M12 4v2M12 18v2" />,
  },
];
