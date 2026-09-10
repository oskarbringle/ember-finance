export const API_BASE_URL = "http://127.0.0.1:8000/api";

export const CHART_COLORS = [
  "#183F35",
  "#D99162",
  "#E9B85F",
  "#73998D",
  "#9A857E",
  "#7A86A8",
  "#C98981",
  "#84937D",
] as const;

export type Transaction = {
  id: number;
  account_id: number;
  transaction_date: string;
  normalized_merchant: string;
  raw_description: string;
  amount: number;
  category: string;
  classification: string;
  confidence: number;
  manually_reviewed: boolean;
};

export type Account = {
  id: number;
  name: string;
  type: string;
  institution: string;
  last_four: string | null;
  current_balance: number;
  balance_mode: string;
  active: boolean;
};

export type ImportPreviewRow = {
  transaction_date: string;
  normalized_merchant: string;
  amount: number;
  category: string;
  classification: string;
};

export type PdfParseReport = {
  provider: string;
  confidence: "high" | "review";
  transactions_found: number;
  searchable_pages: number;
  method: string;
  inflows: number;
  outflows: number;
  net: number;
  warnings: string[];
};

export type ImportPreview = {
  batch_id: string;
  account: string;
  total_rows: number;
  ready_to_import: number;
  committed?: number;
  duplicates: number;
  uncertain: number;
  preview: ImportPreviewRow[];
  parse_report?: PdfParseReport;
  committedDone?: boolean;
};

export type Dashboard = {
  range: { start: string; end: string };
  totals: {
    income: number;
    spending: number;
    saved: number;
    invested: number;
    surplus: number;
    savings_rate: number;
    budget_target: number;
    budget_remaining: number;
    investable_surplus: number;
  };
  categories: { name: string; value: number }[];
  monthly: Record<string, number | string>[];
  net_worth: { date: string; value: number }[];
  budget_categories: { category: string; spent: number; target: number }[];
  recent_transactions: Transaction[];
  review_count: number;
};

export const EMPTY_DASHBOARD: Dashboard = {
  range: { start: "", end: "" },
  totals: {
    income: 0,
    spending: 0,
    saved: 0,
    invested: 0,
    surplus: 0,
    savings_rate: 0,
    budget_target: 0,
    budget_remaining: 0,
    investable_surplus: 0,
  },
  categories: [],
  monthly: [],
  net_worth: [],
  budget_categories: [],
  recent_transactions: [],
  review_count: 0,
};

export function formatCurrency(value: number, compact = false) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: compact ? 0 : 2,
  }).format(value);
}

export function currentMonthLabel() {
  return new Intl.DateTimeFormat("en-US", {
    month: "long",
    year: "numeric",
  }).format(new Date());
}

export async function fetchFinanceData(period: string) {
  const [dashboardResponse, transactionsResponse, accountsResponse] =
    await Promise.all([
      fetch(`${API_BASE_URL}/dashboard?period=${period}`),
      fetch(`${API_BASE_URL}/transactions`),
      fetch(`${API_BASE_URL}/accounts`),
    ]);

  if (
    !dashboardResponse.ok ||
    !transactionsResponse.ok ||
    !accountsResponse.ok
  ) {
    throw new Error("Could not load local finance data");
  }

  return {
    dashboard: (await dashboardResponse.json()) as Dashboard,
    transactions: (await transactionsResponse.json()) as Transaction[],
    accounts: (await accountsResponse.json()) as Account[],
  };
}
