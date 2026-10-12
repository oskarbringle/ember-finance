export const API_BASE_URL = "http://127.0.0.1:8000/api";

export const CHART_COLORS = [
  "#244b42",
  "#d48652",
  "#d9ae55",
  "#668b80",
  "#8b6f68",
  "#6f7699",
  "#b87670",
  "#70866b",
  "#aa8a55",
  "#5f7f94",
  "#9474a0",
  "#89786b",
  "#9aa19c",
] as const;

export type FinanceFilters = {
  period: "this_month" | "last_month" | "last_3_months" | "all_time" | "custom";
  startMonth: string;
  endMonth: string;
  includeWork: boolean;
  includeOneTime: boolean;
  includeTravel: boolean;
};

export type Metrics = {
  month: string;
  total_income: number;
  recurring_income: number;
  total_spending: number;
  personal_spending: number;
  core_spending: number;
  cash_flow_surplus: number;
  retirement_investing: number;
  other_investing: number;
  internal_transfers: number;
  monthly_wealth_added: number;
  wealth_building_rate: number;
};

export type ExpenseEntry = {
  id: number;
  month: string;
  amount: number;
  description: string;
  category: string;
  expense_tag: string;
};

export type IncomeEntry = {
  id: number;
  month: string;
  amount: number;
  description: string;
  income_class: string;
};

export type WealthFlowEntry = {
  id: number;
  month: string;
  amount: number;
  destination: string;
  flow_class: string;
};

export type FinanceData = {
  metadata: {
    workbook_name: string | null;
    imported_at: string | null;
    available_months: string[];
    selected_months: string[];
  };
  metrics: Metrics;
  average_core_spending: number;
  monthly: Metrics[];
  categories: {
    category: string;
    value: number;
    percentage: number;
    count: number;
  }[];
  category_trends: Record<string, number | string>[];
  expenses: ExpenseEntry[];
  all_expenses: ExpenseEntry[];
  income: IncomeEntry[];
  wealth_flows: WealthFlowEntry[];
  net_worth: Record<string, number | string>[];
  net_worth_accounts: {
    account: string;
    account_type: string;
    value: number;
    group: string;
  }[];
  net_worth_composition: { group: string; value: number }[];
  current_net_worth: number;
  insights: string[];
};

export type ImportPreview = {
  token: string;
  workbook_name: string;
  detected_months: string[];
  income_entries: number;
  expense_entries: number;
  wealth_flow_entries: number;
  net_worth_entries: number;
  net_worth_dates: string[];
  issues: {
    sheet: string;
    row: number | null;
    message: string;
    severity: "error" | "warning";
  }[];
  can_import: boolean;
};

export const EMPTY_METRICS: Metrics = {
  month: "",
  total_income: 0,
  recurring_income: 0,
  total_spending: 0,
  personal_spending: 0,
  core_spending: 0,
  cash_flow_surplus: 0,
  retirement_investing: 0,
  other_investing: 0,
  internal_transfers: 0,
  monthly_wealth_added: 0,
  wealth_building_rate: 0,
};

export const EMPTY_DATA: FinanceData = {
  metadata: {
    workbook_name: null,
    imported_at: null,
    available_months: [],
    selected_months: [],
  },
  metrics: EMPTY_METRICS,
  average_core_spending: 0,
  monthly: [],
  categories: [],
  category_trends: [],
  expenses: [],
  all_expenses: [],
  income: [],
  wealth_flows: [],
  net_worth: [],
  net_worth_accounts: [],
  net_worth_composition: [],
  current_net_worth: 0,
  insights: [],
};

export function formatCurrency(value: number, compact = false) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: compact ? 0 : 2,
  }).format(value);
}

export function monthLabel(month: string, short = false) {
  if (!month) return "—";
  const [year, monthNumber] = month.split("-").map(Number);
  return new Intl.DateTimeFormat("en-US", {
    month: short ? "short" : "long",
    year: short ? undefined : "numeric",
  }).format(new Date(year, monthNumber - 1, 1));
}

export async function fetchFinanceData(filters: FinanceFilters) {
  const query = new URLSearchParams({
    period: filters.period,
    include_work_reimbursable: String(filters.includeWork),
    include_one_time: String(filters.includeOneTime),
    include_personal_travel: String(filters.includeTravel),
  });
  if (filters.period === "custom") {
    query.set("start_month", filters.startMonth);
    query.set("end_month", filters.endMonth);
  }
  const response = await fetch(`${API_BASE_URL}/dashboard?${query}`);
  if (!response.ok) throw new Error("Could not load local finance data");
  return (await response.json()) as FinanceData;
}
