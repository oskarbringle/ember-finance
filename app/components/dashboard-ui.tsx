"use client";

import type { ElementType, ReactNode } from "react";
import { Info } from "lucide-react";
import { formatCurrency } from "../lib/finance";

export function MiniLogo() {
  return (
    <div className="brand-mark" aria-hidden="true">
      <span />
      <span />
      <span />
    </div>
  );
}

export function Loading() {
  return (
    <div className="loading" aria-label="Loading dashboard">
      <span />
      <span />
      <span />
    </div>
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`card ${className}`}>{children}</section>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        {eyebrow && <span className="eyebrow">{eyebrow}</span>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </header>
  );
}

export function MetricCard({
  label,
  value,
  detail,
  icon: Icon,
  tooltip,
  accent = false,
}: {
  label: string;
  value: string;
  detail: string;
  icon: ElementType;
  tooltip?: string;
  accent?: boolean;
}) {
  return (
    <Card className={`metric-card ${accent ? "accent" : ""}`}>
      <div className="metric-label">
        <Icon size={15} />
        <span>{label}</span>
        {tooltip && <Info size={13} title={tooltip} />}
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </Card>
  );
}

export function ChartTooltip({
  active,
  payload,
  label,
  percent = false,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color?: string }[];
  label?: string;
  percent?: boolean;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      {label && <strong>{label}</strong>}
      {payload.map((item) => (
        <span key={item.name}>
          <i style={{ background: item.color }} />
          {item.name}:{" "}
          {percent ? `${item.value.toFixed(1)}%` : formatCurrency(item.value)}
        </span>
      ))}
    </div>
  );
}

export function EmptyState({ onImport }: { onImport: () => void }) {
  return (
    <Card className="empty-state">
      <div className="empty-visual">
        <span />
        <span />
        <span />
      </div>
      <h2>Your spreadsheet is the starting point.</h2>
      <p>
        Import your budgeting workbook to turn monthly entries into clear
        trends, comparisons, and net-worth history.
      </p>
      <button className="primary-button" onClick={onImport}>
        Import budgeting workbook
      </button>
    </Card>
  );
}
