"use client";

import type { ElementType, ReactNode } from "react";
import { ArrowDownLeft } from "lucide-react";
import { formatCurrency, type Account, type Transaction } from "../lib/finance";

export function MiniLogo() {
  return (
    <div className="brand-mark">
      <span />
      <span />
      <span />
    </div>
  );
}

export function Loading() {
  return (
    <div className="loading">
      <span />
      <span />
      <span />
    </div>
  );
}

export function Card({
  children,
  className = "",
  onClick,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}) {
  return (
    <section
      className={`card ${className} ${onClick ? "clickable" : ""}`}
      onClick={onClick}
    >
      {children}
    </section>
  );
}

export function ChartTip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number; color?: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <strong>{label}</strong>
      {payload.map((item) => (
        <span key={item.name}>
          <i style={{ background: item.color }} />
          {item.name}: {formatCurrency(item.value, true)}
        </span>
      ))}
    </div>
  );
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
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}

export function MetricCard({
  label,
  value,
  delta,
  tone,
  icon: Icon,
  onClick,
}: {
  label: string;
  value: string;
  delta: string;
  tone?: string;
  icon: ElementType;
  onClick: () => void;
}) {
  return (
    <Card className={`metric ${tone || ""}`} onClick={onClick}>
      <div className="metric-top">
        <span>{label}</span>
        <div className="metric-icon">
          <Icon size={17} />
        </div>
      </div>
      <strong>{value}</strong>
      <small>{delta}</small>
    </Card>
  );
}

export function TransactionTable({
  rows,
  accounts,
  onSelect,
}: {
  rows: Transaction[];
  accounts: Account[];
  onSelect: (row: Transaction) => void;
}) {
  const accountMap = new Map(accounts.map((account) => [account.id, account]));
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Merchant</th>
            <th>Account</th>
            <th>Category</th>
            <th>Classification</th>
            <th>Date</th>
            <th className="align-right">Amount</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((transaction) => (
            <tr key={transaction.id} onClick={() => onSelect(transaction)}>
              <td>
                <div className="merchant-cell">
                  <div
                    className={`merchant-icon ${transaction.amount > 0 ? "in" : ""}`}
                  >
                    {transaction.amount > 0 ? (
                      <ArrowDownLeft size={16} />
                    ) : (
                      transaction.normalized_merchant.charAt(0)
                    )}
                  </div>
                  <div>
                    <strong>{transaction.normalized_merchant}</strong>
                    <small>{transaction.raw_description}</small>
                  </div>
                </div>
              </td>
              <td>
                {accountMap.get(transaction.account_id)?.name ||
                  `Account ${transaction.account_id}`}
              </td>
              <td>
                <span className="category-dot" />
                {transaction.category}
              </td>
              <td>
                <span
                  className={`pill ${transaction.classification.toLowerCase()}`}
                >
                  {transaction.classification.replaceAll("_", " ")}
                </span>
              </td>
              <td>
                {new Date(
                  `${transaction.transaction_date}T12:00:00`,
                ).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                })}
              </td>
              <td
                className={`align-right amount ${transaction.amount > 0 ? "positive" : ""}`}
              >
                {transaction.amount > 0 ? "+" : "−"}
                {formatCurrency(Math.abs(transaction.amount))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
