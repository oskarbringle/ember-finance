"use client";

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  CircleDollarSign,
  CalendarDays,
  Columns3,
  Download,
  Flame,
  House,
  LayoutDashboard,
  Menu,
  PiggyBank,
  Pencil,
  Plus,
  ReceiptText,
  Repeat2,
  Search,
  Settings,
  Sparkles,
  Target,
  Upload,
  WalletCards,
  X,
} from "lucide-react";
import {
  Card,
  ChartTip,
  Loading,
  MetricCard,
  MiniLogo,
  PageHeader,
  TransactionTable,
} from "./components/dashboard-ui";
import {
  API_BASE_URL as API,
  CHART_COLORS as COLORS,
  EMPTY_DASHBOARD,
  fetchFinanceData,
  formatCurrency as money,
  type Account,
  type Dashboard,
  type ImportPreview,
  type Transaction,
} from "./lib/finance";

const nav = [
  ["Home", House],
  ["Overview", LayoutDashboard],
  ["Transactions", ReceiptText],
  ["Spending", CircleDollarSign],
  ["Review", Sparkles],
  ["Compare", Columns3],
  ["Monthly Report", CalendarDays],
  ["FIRE Plan", Flame],
  ["Recurring", Repeat2],
  ["Net Worth", PiggyBank],
  ["Import", Upload],
  ["Settings", Settings],
] as const;

const REPORTING_PERIODS = [
  ["this_month", "This month"],
  ["last_month", "Last month"],
  ["ytd", "Year to date"],
  ["pre_job", "Before job start"],
  ["post_job", "Since job start"],
] as const;

function reportingPeriodLabel(period: string) {
  return (
    REPORTING_PERIODS.find(([value]) => value === period)?.[1] ||
    "Selected period"
  );
}

function ReportingPeriodSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (period: string) => void;
}) {
  return (
    <label className="period-control">
      <span>Reporting period</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {REPORTING_PERIODS.map(([period, label]) => (
          <option key={period} value={period}>
            {label}
          </option>
        ))}
      </select>
    </label>
  );
}

function transactionsInRange(transactions: Transaction[], data: Dashboard) {
  if (!data.range.start || !data.range.end) return [];
  return transactions.filter(
    (transaction) =>
      transaction.transaction_date >= data.range.start &&
      transaction.transaction_date <= data.range.end,
  );
}

type DuplicateGroup = {
  key: string;
  transactions: Transaction[];
};

function findCrossAccountDuplicates(
  transactions: Transaction[],
): DuplicateGroup[] {
  const grouped = transactions.reduce<Map<string, Transaction[]>>(
    (result, transaction) => {
      const description = transaction.raw_description
        .trim()
        .replace(/\s+/g, " ")
        .toUpperCase();
      const key = `${transaction.transaction_date}|${transaction.amount.toFixed(2)}|${description}`;
      result.set(key, [...(result.get(key) || []), transaction]);
      return result;
    },
    new Map(),
  );
  return [...grouped.entries()]
    .filter(
      ([, rows]) =>
        new Set(rows.map((transaction) => transaction.account_id)).size > 1,
    )
    .map(([key, rows]) => ({ key, transactions: rows }));
}

function HomePage({
  accounts,
  transactions,
  reviewCount,
  onNavigate,
}: {
  accounts: Account[];
  transactions: Transaction[];
  reviewCount: number;
  onNavigate: (page: string) => void;
}) {
  const hasAccount = accounts.length > 0;
  const hasImported = transactions.length > 0;
  return (
    <>
      <div className="onboarding">
        <div className="onboarding-hero">
          <div className="eyebrow">
            {hasAccount ? "Your setup guide" : "Welcome to Ember"}
          </div>
          <h1>
            {hasAccount
              ? "Build your financial picture."
              : "Start with a clean slate."}
          </h1>
          <p>
            Ember starts empty and builds the dashboard from transactions you
            verify. Create the account shown on your statement, preview the PDF
            extraction, then approve only rows that match the statement.
          </p>
          <button
            className="primary"
            onClick={() => onNavigate(hasAccount ? "Import" : "Settings")}
          >
            {hasAccount ? <Upload size={16} /> : <Plus size={16} />}
            {hasAccount ? "Import a statement" : "Create your first account"}
          </button>
        </div>
        <div className="onboarding-proof">
          <span>LOCAL BY DEFAULT</span>
          <strong>Your data stays yours.</strong>
          <p>
            Statements are read on this computer. Nothing is added until you
            inspect the preview and choose Import.
          </p>
          <div>
            <Check size={15} /> No bank login or cloud account
          </div>
          <div>
            <Check size={15} /> PDF and CSV preview before saving
          </div>
          <div>
            <Check size={15} /> Duplicate checks on every import
          </div>
        </div>
      </div>
      <div className="onboarding-steps">
        <Card className={hasAccount ? "complete" : ""}>
          <b>01</b>
          <div>
            <span>{hasAccount ? "COMPLETE" : "START HERE"}</span>
            <strong>Create the statement&apos;s account</strong>
            <p>
              Add a nickname, bank, account type, and current balance. Only the
              optional last four digits are needed—never a full account number.
            </p>
            <button onClick={() => onNavigate("Settings")}>
              {hasAccount ? "View or edit accounts" : "Create account"}
            </button>
          </div>
        </Card>
        <Card className={hasImported ? "complete" : ""}>
          <b>02</b>
          <div>
            <span>{hasImported ? "COMPLETE" : "NEXT"}</span>
            <strong>Preview a PDF or CSV</strong>
            <p>
              Choose the matching account, upload the full statement, and check
              the extracted row count, dates, descriptions, and signed totals.
            </p>
            <button onClick={() => onNavigate("Import")}>Open import</button>
          </div>
        </Card>
        <Card className={hasImported && reviewCount === 0 ? "complete" : ""}>
          <b>03</b>
          <div>
            <span>
              {hasImported && reviewCount === 0 ? "COMPLETE" : "THEN REVIEW"}
            </span>
            <strong>Confirm uncertain activity</strong>
            <p>
              Resolve ambiguous transfers or merchants so spending, saving, and
              income are counted correctly across the dashboard.
            </p>
            <button onClick={() => onNavigate("Review")}>Open review</button>
          </div>
        </Card>
      </div>
      <div className="home-explainers">
        <Card>
          <span>WHAT “SEARCHABLE PDF” MEANS</span>
          <h2>Text can be selected inside the statement.</h2>
          <p>
            If the PDF is an image scan, run local OCR first. Ember will never
            guess transactions from an unreadable document.
          </p>
        </Card>
        <Card>
          <span>WHAT TO VERIFY</span>
          <h2>Row count, dates, amounts, and direction.</h2>
          <p>
            Money out should appear negative and deposits positive. Compare the
            preview totals with the statement before importing.
          </p>
        </Card>
        <Card>
          <span>HOW THE DASHBOARD WORKS</span>
          <h2>Transfers are separated from real spending.</h2>
          <p>
            Card payments and internal transfers are excluded from spending to
            avoid counting the same money twice.
          </p>
        </Card>
      </div>
    </>
  );
}

function Overview({
  data,
  transactions,
  accounts,
  onNavigate,
  onFilter,
  onSelect,
  period,
  onPeriodChange,
}: {
  data: Dashboard;
  transactions: Transaction[];
  accounts: Account[];
  onNavigate: (page: string) => void;
  onFilter: (kind: string) => void;
  onSelect: (tx: Transaction) => void;
  period: string;
  onPeriodChange: (period: string) => void;
}) {
  const savingsTrend = data.monthly.map((row) => ({
    month: row.month,
    rate: row.income
      ? Math.round(
          ((Number(row.saving) + Number(row.investing)) / Number(row.income)) *
            100,
        )
      : 0,
  }));
  return (
    <>
      <PageHeader
        eyebrow={reportingPeriodLabel(period)}
        title="Your money, in focus."
        description={
          transactions.length
            ? `The selected period’s savings rate is ${data.totals.savings_rate}%. Every number opens to the transactions behind it.`
            : "Your accounts are ready. Import a statement to begin building an explainable financial picture."
        }
        action={
          <div className="page-actions">
            <ReportingPeriodSelect value={period} onChange={onPeriodChange} />
            <button className="primary" onClick={() => onNavigate("Import")}>
              <Upload size={16} /> Import transactions
            </button>
          </div>
        }
      />
      <div className="metrics-grid">
        <MetricCard
          label="Total income"
          value={money(data.totals.income, true)}
          delta="Earned income only"
          tone="income"
          icon={ArrowDownLeft}
          onClick={() => onFilter("INCOME")}
        />
        <MetricCard
          label="Spending"
          value={money(data.totals.spending, true)}
          delta="Expenses net of refunds"
          icon={ArrowUpRight}
          onClick={() => onFilter("EXPENSE")}
        />
        <MetricCard
          label="Saved + invested"
          value={money(data.totals.saved + data.totals.invested, true)}
          delta={`${money(data.totals.saved, true)} saved · ${money(data.totals.invested, true)} invested`}
          icon={PiggyBank}
          onClick={() => onFilter("SAVED_PLUS_INVESTED")}
        />
        <MetricCard
          label="Savings rate"
          value={`${data.totals.savings_rate}%`}
          delta="Saved + invested ÷ earned income"
          tone="rate"
          icon={Target}
          onClick={() => onNavigate("FIRE Plan")}
        />
        <MetricCard
          label="Budget remaining"
          value={money(data.totals.budget_remaining, true)}
          delta={
            data.totals.budget_target
              ? `${Math.round((data.totals.spending / data.totals.budget_target) * 100)}% of monthly plan used`
              : "Set a monthly target in Settings"
          }
          icon={WalletCards}
          onClick={() => onNavigate("Settings")}
        />
        <MetricCard
          label="Available to invest"
          value={money(data.totals.investable_surplus, true)}
          delta="Unused budget → FIRE"
          tone="fire"
          icon={Flame}
          onClick={() => onNavigate("FIRE Plan")}
        />
      </div>
      <div className="grid-main">
        <Card className="chart-card spend-chart">
          <div className="card-heading">
            <div>
              <span>SPENDING BY CATEGORY</span>
              <h2>{money(data.totals.spending, true)}</h2>
            </div>
            <button
              className="text-button"
              onClick={() => onNavigate("Spending")}
            >
              View details <ArrowRight size={14} />
            </button>
          </div>
          <div className="donut-layout">
            <div className="donut-wrap">
              <ResponsiveContainer width="100%" height={255}>
                <PieChart>
                  <Pie
                    data={data.categories}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={72}
                    outerRadius={103}
                    paddingAngle={2}
                    stroke="none"
                    onClick={(entry) => onFilter(String(entry.name))}
                  >
                    {data.categories.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<ChartTip />} />
                </PieChart>
              </ResponsiveContainer>
              <div className="donut-center">
                <small>Spent</small>
                <strong>{money(data.totals.spending, true)}</strong>
                <span>of {money(data.totals.budget_target, true)}</span>
              </div>
            </div>
            <div className="legend">
              {data.categories.slice(0, 6).map((item, i) => (
                <button key={item.name} onClick={() => onFilter(item.name)}>
                  <i style={{ background: COLORS[i % COLORS.length] }} />
                  <span>{item.name}</span>
                  <strong>{money(item.value, true)}</strong>
                </button>
              ))}
            </div>
          </div>
        </Card>
        <Card className="chart-card">
          <div className="card-heading">
            <div>
              <span>CASH FLOW</span>
              <h2>Money in & out</h2>
            </div>
            <span className="badge">6 months</span>
          </div>
          <ResponsiveContainer width="100%" height={290}>
            <BarChart data={data.monthly} barGap={3}>
              <CartesianGrid vertical={false} stroke="#EDF0EC" />
              <XAxis
                dataKey="month"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#7C847F", fontSize: 12 }}
              />
              <YAxis hide />
              <Tooltip content={<ChartTip />} />
              <Bar
                dataKey="income"
                name="Income"
                fill="#183F35"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="spending"
                name="Spending"
                fill="#D99162"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="saving"
                name="Saved"
                fill="#AAC2B6"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
          <div className="chart-key">
            <span>
              <i className="green" />
              Income
            </span>
            <span>
              <i className="orange" />
              Spending
            </span>
            <span>
              <i className="sage" />
              Saved
            </span>
          </div>
        </Card>
      </div>
      <div className="grid-secondary">
        {data.totals.budget_target ? (
          <Card className="budget-card">
            <div className="card-heading">
              <div>
                <span>BUDGET STATUS</span>
                <h2>
                  {data.totals.budget_remaining >= 0
                    ? "Comfortably on track"
                    : "Above target"}
                </h2>
              </div>
              <span className="status-good">
                <Check size={14} />{" "}
                {data.totals.budget_remaining >= 0
                  ? "Under budget"
                  : "Review plan"}
              </span>
            </div>
            <div className="budget-total">
              <div>
                <span>Monthly spending</span>
                <strong>
                  {money(data.totals.spending, true)}{" "}
                  <small>/ {money(data.totals.budget_target, true)}</small>
                </strong>
              </div>
              <strong className="remaining">
                {money(Math.abs(data.totals.budget_remaining), true)}{" "}
                {data.totals.budget_remaining >= 0 ? "left" : "over"}
              </strong>
            </div>
            <div className="progress large">
              <span
                style={{
                  width: `${Math.min((data.totals.spending / data.totals.budget_target) * 100, 100)}%`,
                }}
              />
            </div>
            <div className="budget-lines">
              {data.budget_categories.map((item) => (
                <button
                  key={item.category}
                  onClick={() => onFilter(item.category)}
                >
                  <div>
                    <span>{item.category}</span>
                    <strong>
                      {money(item.spent, true)} / {money(item.target, true)}
                    </strong>
                  </div>
                  <div className="progress">
                    <span
                      style={{
                        width: `${item.target ? Math.min((item.spent / item.target) * 100, 100) : 0}%`,
                      }}
                    />
                  </div>
                </button>
              ))}
            </div>
            <div className="fire-callout">
              <Flame size={20} />
              <div>
                <span>Potential FIRE contribution</span>
                <strong>{money(data.totals.investable_surplus, true)}</strong>
              </div>
              <p>
                This is unused budget—not automatic income or a duplicated
                transfer.
              </p>
            </div>
          </Card>
        ) : (
          <Card className="budget-card empty-budget">
            <Target size={24} />
            <h2>Set your first monthly target</h2>
            <p>
              Ember never invents a budget from demo data. Add your own broad
              spending, saving, and investing targets in Settings.
            </p>
            <button
              className="secondary"
              onClick={() => onNavigate("Settings")}
            >
              Set budget targets
            </button>
          </Card>
        )}
        <Card className="chart-card">
          <div className="card-heading">
            <div>
              <span>SAVINGS RATE</span>
              <h2>
                {data.totals.savings_rate}% <small>this month</small>
              </h2>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={255}>
            <AreaChart data={savingsTrend}>
              <defs>
                <linearGradient id="rateFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0" stopColor="#234F42" stopOpacity={0.22} />
                  <stop offset="1" stopColor="#234F42" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#EDF0EC" />
              <XAxis
                dataKey="month"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#7C847F", fontSize: 12 }}
              />
              <YAxis hide domain={[0, 50]} />
              <Tooltip content={<ChartTip />} />
              <Area
                type="monotone"
                dataKey="rate"
                name="Savings rate %"
                stroke="#234F42"
                strokeWidth={2.5}
                fill="url(#rateFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <Card className="transactions-card">
        <div className="card-heading">
          <div>
            <span>RECENT ACTIVITY</span>
            <h2>Recent transactions</h2>
          </div>
          <button
            className="text-button"
            onClick={() => onNavigate("Transactions")}
          >
            View all <ArrowRight size={14} />
          </button>
        </div>
        <TransactionTable
          rows={(data.recent_transactions.length
            ? data.recent_transactions
            : transactions
          ).slice(0, 7)}
          accounts={accounts}
          onSelect={onSelect}
        />
      </Card>
    </>
  );
}

function TransactionsPage({
  transactions,
  accounts,
  initialFilter,
  onSelect,
}: {
  transactions: Transaction[];
  accounts: Account[];
  initialFilter: string;
  onSelect: (tx: Transaction) => void;
}) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState(initialFilter);
  const rows = transactions
    .filter(
      (tx) =>
        !filter ||
        [tx.classification, tx.category, tx.normalized_merchant].includes(
          filter,
        ) ||
        (filter === "SAVED_PLUS_INVESTED" &&
          ["SAVING", "INVESTMENT"].includes(tx.classification)),
    )
    .filter((tx) =>
      `${tx.normalized_merchant} ${tx.raw_description} ${tx.category}`
        .toLowerCase()
        .includes(query.toLowerCase()),
    );
  return (
    <>
      <PageHeader
        eyebrow="Ledger"
        title="Every dollar, accounted for."
        description="Search, filter, and open any transaction to see exactly how it affects your numbers."
      />
      <Card className="toolbar">
        <div className="search">
          <Search size={17} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search merchant or description"
          />
        </div>
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          aria-label="Filter classification"
        >
          <option value="">All activity</option>
          <option>EXPENSE</option>
          <option>INCOME</option>
          <option>SAVING</option>
          <option>INVESTMENT</option>
          <option>CREDIT_CARD_PAYMENT</option>
          <option>TRANSFER</option>
          <option>UNKNOWN</option>
        </select>
      </Card>
      <Card className="transactions-card full">
        <div className="card-heading">
          <div>
            <span>TRANSACTIONS</span>
            <h2>{rows.length} records</h2>
          </div>
          <span className="muted">
            Transfers and card payments excluded from spending
          </span>
        </div>
        <TransactionTable rows={rows} accounts={accounts} onSelect={onSelect} />
      </Card>
    </>
  );
}

function SpendingPage({
  data,
  transactions,
  onFilter,
  period,
  onPeriodChange,
}: {
  data: Dashboard;
  transactions: Transaction[];
  onFilter: (category: string) => void;
  period: string;
  onPeriodChange: (period: string) => void;
}) {
  const expenses = transactionsInRange(transactions, data).filter(
    (tx) => tx.classification === "EXPENSE",
  );
  const merchantSpend = Object.entries(
    expenses.reduce<Record<string, number>>((acc, tx) => {
      acc[tx.normalized_merchant] =
        (acc[tx.normalized_merchant] || 0) + Math.abs(tx.amount);
      return acc;
    }, {}),
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);
  const largest = [...expenses]
    .sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount))
    .slice(0, 4);
  return (
    <>
      <PageHeader
        eyebrow="Spending intelligence"
        title="See where it really goes."
        description="Refunds and reimbursements are netted against spending. Transfers never appear here."
        action={
          <ReportingPeriodSelect value={period} onChange={onPeriodChange} />
        }
      />
      <div className="three-stats">
        <Card>
          <span>Total spending</span>
          <strong>{money(data.totals.spending)}</strong>
          <small>Expenses net of refunds</small>
        </Card>
        <Card>
          <span>Transactions</span>
          <strong>{expenses.length}</strong>
          <small>
            Across {new Set(expenses.map((x) => x.account_id)).size} accounts
          </small>
        </Card>
        <Card>
          <span>Average purchase</span>
          <strong>
            {money(
              expenses.length ? data.totals.spending / expenses.length : 0,
            )}
          </strong>
          <small>Expense transactions only</small>
        </Card>
      </div>
      <div className="grid-main">
        <Card className="chart-card">
          <div className="card-heading">
            <div>
              <span>CATEGORY MIX</span>
              <h2>Spending composition</h2>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={data.categories} layout="vertical">
              <CartesianGrid horizontal={false} stroke="#EDF0EC" />
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="name"
                axisLine={false}
                tickLine={false}
                width={105}
                tick={{ fill: "#505854", fontSize: 12 }}
              />
              <Tooltip content={<ChartTip />} />
              <Bar
                dataKey="value"
                name="Spent"
                fill="#315C4E"
                radius={[0, 5, 5, 0]}
                onClick={(entry) => onFilter(String(entry.name))}
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card>
          <div className="card-heading">
            <div>
              <span>TOP MERCHANTS</span>
              <h2>Where you spend most</h2>
            </div>
          </div>
          <div className="rank-list">
            {merchantSpend.map(([name, value], i) => (
              <button key={name} onClick={() => onFilter(name)}>
                <b>{i + 1}</b>
                <span>{name}</span>
                <strong>{money(value)}</strong>
              </button>
            ))}
          </div>
        </Card>
      </div>
      <Card>
        <div className="card-heading">
          <div>
            <span>LARGEST PURCHASES</span>
            <h2>This period</h2>
          </div>
        </div>
        <div className="purchase-grid">
          {largest.map((tx) => (
            <button key={tx.id} onClick={() => onFilter(tx.category)}>
              <span>{tx.category}</span>
              <strong>{tx.normalized_merchant}</strong>
              <b>{money(Math.abs(tx.amount))}</b>
              <small>
                {new Date(`${tx.transaction_date}T12:00`).toLocaleDateString(
                  "en-US",
                  { month: "short", day: "numeric" },
                )}
              </small>
            </button>
          ))}
        </div>
      </Card>
    </>
  );
}

function ComparePage({
  transactions,
  onFilter,
}: {
  transactions: Transaction[];
  onFilter: (category: string) => void;
}) {
  const now = new Date();
  const currentKey = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  const previousDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const previousKey = `${previousDate.getFullYear()}-${String(previousDate.getMonth() + 1).padStart(2, "0")}`;
  function categorySpend(month: string) {
    return transactions
      .filter((tx) => tx.transaction_date.startsWith(month))
      .reduce<Record<string, number>>((acc, tx) => {
        if (tx.classification === "EXPENSE" && tx.amount < 0)
          acc[tx.category] = (acc[tx.category] || 0) + Math.abs(tx.amount);
        if (
          ["REFUND", "REIMBURSEMENT"].includes(tx.classification) &&
          tx.amount > 0
        )
          acc[tx.category] = (acc[tx.category] || 0) - tx.amount;
        return acc;
      }, {});
  }
  const current = categorySpend(currentKey);
  const previousCategories = categorySpend(previousKey);
  const currentTotal = Object.values(current).reduce((a, b) => a + b, 0);
  const previousTotal = Object.values(previousCategories).reduce(
    (a, b) => a + b,
    0,
  );
  const categories = Array.from(
    new Set([...Object.keys(previousCategories), ...Object.keys(current)]),
  )
    .map((name) => {
      const a = Number(current[name] || 0),
        b = Number(previousCategories[name] || 0),
        delta = a - b;
      return {
        name,
        current: a,
        previous: b,
        delta,
        percent: b ? Math.round((delta / b) * 100) : 0,
      };
    })
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));
  const totalDelta = currentTotal - previousTotal;
  const percent = previousTotal
    ? Math.abs(Math.round((totalDelta / previousTotal) * 100))
    : 0;
  return (
    <>
      <PageHeader
        eyebrow="Comparison"
        title="What changed—and where."
        description="Compare the same accounting definitions across periods. Lower spending is shown as a favorable change, without judgment."
      />
      {transactions.length ? (
        <>
          <div className="compare-hero">
            <div>
              <span>TOTAL SPENDING</span>
              <strong>{money(currentTotal)}</strong>
              <small>This month</small>
            </div>
            <ArrowRight size={22} />
            <div>
              <span>LAST MONTH</span>
              <strong>{money(previousTotal)}</strong>
              <small>
                {previousDate.toLocaleDateString("en-US", {
                  month: "long",
                  year: "numeric",
                })}
              </small>
            </div>
            <div className={totalDelta <= 0 ? "favorable" : "unfavorable"}>
              <b>
                {totalDelta <= 0 ? "↓" : "↑"} {money(Math.abs(totalDelta))}
              </b>
              <span>
                {percent}% {totalDelta <= 0 ? "less" : "more"}
              </span>
            </div>
          </div>
          <Card className="compare-card">
            <div className="card-heading">
              <div>
                <span>CATEGORY CHANGES</span>
                <h2>Month-over-month detail</h2>
              </div>
              <span className="muted">
                Click any row to see its transactions
              </span>
            </div>
            <div className="compare-table">
              <div className="compare-row header">
                <span>Category</span>
                <span>This month</span>
                <span>Last month</span>
                <span>Change</span>
                <span>Direction</span>
              </div>
              {categories.map((row) => (
                <button
                  className="compare-row"
                  key={row.name}
                  onClick={() => onFilter(row.name)}
                >
                  <strong>{row.name}</strong>
                  <span>{money(row.current)}</span>
                  <span>{money(row.previous)}</span>
                  <span>
                    {row.delta > 0 ? "+" : "−"}
                    {money(Math.abs(row.delta))}
                  </span>
                  <b className={row.delta <= 0 ? "favorable" : "unfavorable"}>
                    {row.delta <= 0 ? "↓" : "↑"} {Math.abs(row.percent)}%
                  </b>
                </button>
              ))}
            </div>
          </Card>
        </>
      ) : (
        <Card className="empty">
          <h2>No periods to compare yet</h2>
          <p>
            Import transactions from at least one statement to build a factual
            comparison.
          </p>
        </Card>
      )}
    </>
  );
}

function MonthlyReportPage({
  data,
  transactions,
  onFilter,
  period,
  onPeriodChange,
}: {
  data: Dashboard;
  transactions: Transaction[];
  onFilter: (value: string) => void;
  period: string;
  onPeriodChange: (period: string) => void;
}) {
  const periodTransactions = transactionsInRange(transactions, data);
  const expenses = periodTransactions
    .filter((tx) => tx.classification === "EXPENSE")
    .sort((a, b) => Math.abs(b.amount) - Math.abs(a.amount));
  const merchants = Object.entries(
    expenses.reduce<Record<string, number>>((acc, tx) => {
      acc[tx.normalized_merchant] =
        (acc[tx.normalized_merchant] || 0) + Math.abs(tx.amount);
      return acc;
    }, {}),
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
  return (
    <>
      <PageHeader
        eyebrow="Monthly summary"
        title={`${reportingPeriodLabel(period)}, at a glance.`}
        description="A factual close-up of income, spending, saving, investing, and the changes that shaped the month."
        action={
          <div className="page-actions">
            <ReportingPeriodSelect value={period} onChange={onPeriodChange} />
            <a className="secondary" href={`${API}/export/transactions.csv`}>
              <Download size={16} /> Export full ledger
            </a>
          </div>
        }
      />
      {periodTransactions.length ? (
        <>
          <Card className="report-hero">
            <div>
              <span>MONTHLY OUTCOME</span>
              <h2>
                {money(data.totals.investable_surplus)} available to save or
                invest
              </h2>
              <p>
                {data.totals.budget_target
                  ? `${money(Math.abs(data.totals.budget_remaining))} ${data.totals.budget_remaining >= 0 ? "under" : "over"} your ${money(data.totals.budget_target)} target.`
                  : "Set a budget target to calculate investable surplus."}
              </p>
            </div>
            <div className="report-score">
              <strong>{data.totals.savings_rate}%</strong>
              <span>savings rate</span>
            </div>
          </Card>
          <div className="report-metrics">
            {[
              ["Income", data.totals.income],
              ["Spending", data.totals.spending],
              ["Saved", data.totals.saved],
              ["Invested", data.totals.invested],
            ].map(([label, value]) => (
              <Card
                key={String(label)}
                onClick={() =>
                  onFilter(
                    label === "Income"
                      ? "INCOME"
                      : label === "Spending"
                        ? "EXPENSE"
                        : label === "Saved"
                          ? "SAVING"
                          : "INVESTMENT",
                  )
                }
              >
                <span>{label}</span>
                <strong>{money(Number(value))}</strong>
              </Card>
            ))}
          </div>
          <div className="grid-main">
            <Card>
              <div className="card-heading">
                <div>
                  <span>TOP CATEGORIES</span>
                  <h2>Where spending concentrated</h2>
                </div>
              </div>
              <div className="report-list">
                {data.categories.slice(0, 5).map((item, i) => (
                  <button key={item.name} onClick={() => onFilter(item.name)}>
                    <i style={{ background: COLORS[i] }} />
                    <span>{item.name}</span>
                    <strong>{money(item.value)}</strong>
                    <small>
                      {data.totals.spending
                        ? Math.round((item.value / data.totals.spending) * 100)
                        : 0}
                      %
                    </small>
                  </button>
                ))}
              </div>
            </Card>
            <Card>
              <div className="card-heading">
                <div>
                  <span>TOP MERCHANTS</span>
                  <h2>Largest destinations</h2>
                </div>
              </div>
              <div className="report-list">
                {merchants.map(([name, value], i) => (
                  <button key={name} onClick={() => onFilter(name)}>
                    <b>{i + 1}</b>
                    <span>{name}</span>
                    <strong>{money(value)}</strong>
                  </button>
                ))}
              </div>
            </Card>
          </div>
          <Card>
            <div className="card-heading">
              <div>
                <span>LARGEST PURCHASES</span>
                <h2>The transactions behind the month</h2>
              </div>
            </div>
            <div className="purchase-grid">
              {expenses.slice(0, 4).map((tx) => (
                <button key={tx.id} onClick={() => onFilter(tx.category)}>
                  <span>{tx.category}</span>
                  <strong>{tx.normalized_merchant}</strong>
                  <b>{money(Math.abs(tx.amount))}</b>
                  <small>{tx.transaction_date}</small>
                </button>
              ))}
            </div>
          </Card>
        </>
      ) : (
        <Card className="empty">
          <h2>No monthly report yet</h2>
          <p>Your first approved import will create this report.</p>
        </Card>
      )}
    </>
  );
}

function ReviewPage({
  rows,
  accounts,
  onReview,
  onResolveDuplicates,
}: {
  rows: Transaction[];
  accounts: Account[];
  onReview: (tx: Transaction, classification: string, category: string) => void;
  onResolveDuplicates: (
    transactions: Transaction[],
    keepAccountId: number,
  ) => Promise<void>;
}) {
  const uncertain = rows.filter(
    (tx) =>
      !tx.manually_reviewed &&
      (tx.classification === "UNKNOWN" || tx.confidence < 0.6),
  );
  const duplicateGroups = findCrossAccountDuplicates(rows);
  const [activeId, setActiveId] = useState<number | null>(
    uncertain[0]?.id || null,
  );
  const [activeDuplicateKey, setActiveDuplicateKey] = useState<string | null>(
    duplicateGroups[0]?.key || null,
  );
  const [duplicateError, setDuplicateError] = useState("");
  const [resolvingDuplicates, setResolvingDuplicates] = useState(false);
  const active =
    uncertain.find((tx) => tx.id === activeId) || uncertain[0] || null;
  const activeDuplicate =
    duplicateGroups.find((group) => group.key === activeDuplicateKey) ||
    duplicateGroups[0] ||
    null;
  const choices = active
    ? active.amount > 0
      ? [
          ["Income", "INCOME", "Other Income"],
          ["Reimbursement", "REIMBURSEMENT", "Reimbursement"],
          ["Refund", "REFUND", "Refund"],
          ["Transfer", "TRANSFER", "Internal Transfer"],
          ["Other income", "INCOME", "Other Income"],
        ]
      : [
          ["Housing", "EXPENSE", "Housing"],
          ["Dining", "EXPENSE", "Dining"],
          ["Transfer", "TRANSFER", "Internal Transfer"],
          ["Saving", "SAVING", "Savings Transfer"],
          ["Investment", "INVESTMENT", "Investment Contribution"],
          ["Other expense", "EXPENSE", "Miscellaneous"],
        ]
    : [];
  if (activeDuplicate) {
    const accountIds = [
      ...new Set(
        activeDuplicate.transactions.map(
          (transaction) => transaction.account_id,
        ),
      ),
    ];
    const sample = activeDuplicate.transactions[0];
    const bulkOptions = accounts
      .map((account) => ({
        account,
        groups: duplicateGroups.filter((group) =>
          group.transactions.some(
            (transaction) => transaction.account_id === account.id,
          ),
        ),
      }))
      .filter((option) => option.groups.length > 1);
    async function keepGroups(groups: DuplicateGroup[], accountId: number) {
      setResolvingDuplicates(true);
      setDuplicateError("");
      try {
        await onResolveDuplicates(
          groups.flatMap((group) => group.transactions),
          accountId,
        );
        setActiveDuplicateKey(null);
      } catch {
        setDuplicateError("Could not resolve these duplicates. Try again.");
      } finally {
        setResolvingDuplicates(false);
      }
    }
    return (
      <>
        <PageHeader
          eyebrow="Duplicate check"
          title="Choose where this transaction belongs."
          description="These are exact matches across different accounts. Ember preserves matching rows in the account you choose and removes only the cross-account copies."
        />
        <div className="review-layout">
          <Card className="review-list">
            <div className="review-count">
              {duplicateGroups.length} duplicate groups
            </div>
            {duplicateGroups.map((group) => (
              <button
                className={activeDuplicate.key === group.key ? "active" : ""}
                key={group.key}
                onClick={() => setActiveDuplicateKey(group.key)}
              >
                <div className="merchant-icon">
                  {group.transactions[0].normalized_merchant.charAt(0)}
                </div>
                <div>
                  <strong>{group.transactions[0].normalized_merchant}</strong>
                  <small>{group.transactions[0].transaction_date}</small>
                </div>
                <b>{group.transactions.length} copies</b>
              </button>
            ))}
          </Card>
          <Card className="review-card">
            <span className="badge warm">EXACT CROSS-ACCOUNT MATCH</span>
            <div className="review-merchant">
              <div className="merchant-icon large">
                {sample.normalized_merchant.charAt(0)}
              </div>
              <div>
                <h2>{sample.normalized_merchant}</h2>
                <p>{sample.raw_description}</p>
              </div>
              <strong>
                {sample.amount > 0 ? "+" : "−"}
                {money(Math.abs(sample.amount))}
              </strong>
            </div>
            <div className="review-question duplicate-question">
              <span>Which account should keep it?</span>
              <div>
                {accountIds.map((accountId) => (
                  <button
                    disabled={resolvingDuplicates}
                    key={accountId}
                    onClick={() => keepGroups([activeDuplicate], accountId)}
                  >
                    Keep in{" "}
                    {accounts.find((account) => account.id === accountId)
                      ?.name || "this account"}
                  </button>
                ))}
              </div>
              {duplicateError && <p className="form-error">{duplicateError}</p>}
            </div>
            {bulkOptions.length > 0 && (
              <div className="bulk-duplicate-actions">
                <span>Imported a whole statement into the wrong account?</span>
                <p>
                  Resolve every exact cross-account match for one account at
                  once. Transactions unique to either account are untouched.
                </p>
                <div>
                  {bulkOptions.map(({ account, groups }) => (
                    <button
                      className="secondary"
                      disabled={resolvingDuplicates}
                      key={account.id}
                      onClick={() => keepGroups(groups, account.id)}
                    >
                      Keep {groups.length} matches in {account.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="review-note">
              <Sparkles size={18} />
              <p>
                Repeated purchases inside the account you keep are preserved.
                Only matching copies assigned to another account are removed.
              </p>
            </div>
          </Card>
        </div>
      </>
    );
  }
  if (!active)
    return (
      <>
        <PageHeader
          eyebrow="Review inbox"
          title="Everything is explained."
          description="There are no uncertain transactions waiting for you."
        />
        <Card className="empty">
          <div className="empty-check">
            <Check size={26} />
          </div>
          <h2>Inbox zero</h2>
          <p>
            New ambiguous transactions—especially Zelle, Venmo, and Cash
            App—will appear here.
          </p>
        </Card>
      </>
    );
  return (
    <>
      <PageHeader
        eyebrow="Review inbox"
        title="A few transactions need context."
        description="Your decision wins over automation, and you choose whether a future rule is created."
      />
      <div className="review-layout">
        <Card className="review-list">
          <div className="review-count">{uncertain.length} to review</div>
          {uncertain.map((tx) => (
            <button
              className={active.id === tx.id ? "active" : ""}
              key={tx.id}
              onClick={() => setActiveId(tx.id)}
            >
              <div className="merchant-icon">
                {tx.normalized_merchant.charAt(0)}
              </div>
              <div>
                <strong>{tx.normalized_merchant}</strong>
                <small>{tx.raw_description}</small>
              </div>
              <b>
                {tx.amount > 0 ? "+" : "−"}
                {money(Math.abs(tx.amount))}
              </b>
            </button>
          ))}
        </Card>
        <Card className="review-card">
          <span className="badge warm">
            LOW CONFIDENCE · {Math.round(active.confidence * 100)}%
          </span>
          <div className="review-merchant">
            <div className="merchant-icon large">
              {active.normalized_merchant.charAt(0)}
            </div>
            <div>
              <h2>{active.normalized_merchant}</h2>
              <p>{active.raw_description}</p>
            </div>
            <strong>
              {active.amount > 0 ? "+" : "−"}
              {money(Math.abs(active.amount))}
            </strong>
          </div>
          <div className="review-question">
            <span>What was this?</span>
            <div>
              {choices.map(([label, classification, category]) => (
                <button
                  key={label}
                  onClick={() => {
                    onReview(active, classification, category);
                    setActiveId(null);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <div className="review-note">
            <Sparkles size={18} />
            <p>
              <strong>You stay in control.</strong> Ember learns this merchant
              for future imports and updates matching unreviewed transactions
              now. Person-to-person payments are never learned automatically.
            </p>
          </div>
        </Card>
      </div>
    </>
  );
}

function FirePage({
  data,
  period,
  onPeriodChange,
}: {
  data: Dashboard;
  period: string;
  onPeriodChange: (period: string) => void;
}) {
  const fireData = data.monthly.map((row) => ({
    month: row.month,
    contribution: Number(row.saving) + Number(row.investing),
    rate: row.income
      ? Math.round(
          ((Number(row.saving) + Number(row.investing)) / Number(row.income)) *
            100,
        )
      : 0,
  }));
  const periodContributions = fireData.reduce(
    (sum, row) => sum + row.contribution,
    0,
  );
  return (
    <>
      <PageHeader
        eyebrow="FIRE progress"
        title="Turn the gap into freedom."
        description="Savings rate = savings plus investment contributions ÷ earned income. Transfers and reimbursements are excluded."
        action={
          <ReportingPeriodSelect value={period} onChange={onPeriodChange} />
        }
      />
      <div className="fire-hero">
        <div>
          <span>INVESTABLE SURPLUS</span>
          <strong>{money(data.totals.investable_surplus)}</strong>
          <p>
            {data.totals.budget_target
              ? "Your unused monthly budget is available to save or invest."
              : "Set your own monthly budget to calculate unused FIRE money."}
          </p>
        </div>
        <div
          className="fire-ring"
          style={
            {
              "--progress": `${data.totals.savings_rate * 3.6}deg`,
            } as CSSProperties
          }
        >
          <span>
            <strong>{data.totals.savings_rate}%</strong>
            <small>savings rate</small>
          </span>
        </div>
      </div>
      <div className="three-stats">
        <Card>
          <span>Saved this month</span>
          <strong>{money(data.totals.saved)}</strong>
          <small>Classified savings transfers</small>
        </Card>
        <Card>
          <span>Invested this month</span>
          <strong>{money(data.totals.invested)}</strong>
          <small>Classified contributions</small>
        </Card>
        <Card>
          <span>Selected-period contributions</span>
          <strong>{money(periodContributions)}</strong>
          <small>Saved + invested</small>
        </Card>
      </div>
      <Card className="chart-card">
        <div className="card-heading">
          <div>
            <span>MOMENTUM</span>
            <h2>Savings rate trend</h2>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={330}>
          <LineChart data={fireData}>
            <CartesianGrid vertical={false} stroke="#E6EAE5" />
            <XAxis dataKey="month" axisLine={false} tickLine={false} />
            <YAxis
              domain={[0, 50]}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<ChartTip />} />
            <Line
              type="monotone"
              dataKey="rate"
              name="Savings rate %"
              stroke="#D48A55"
              strokeWidth={3}
              dot={{ r: 4, fill: "#D48A55" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </Card>
    </>
  );
}

function RecurringPage({ transactions }: { transactions: Transaction[] }) {
  const groups = Object.values(
    transactions
      .filter((tx) => tx.classification === "EXPENSE")
      .reduce<Record<string, Transaction[]>>((acc, tx) => {
        (acc[tx.normalized_merchant] ??= []).push(tx);
        return acc;
      }, {}),
  );
  const recurring = groups
    .filter((rows) => rows.length >= 2)
    .map((rows) => {
      const ordered = [...rows].sort((a, b) =>
        a.transaction_date.localeCompare(b.transaction_date),
      );
      const avg =
        ordered.reduce((s, row) => s + Math.abs(row.amount), 0) /
        ordered.length;
      return {
        merchant: ordered[0].normalized_merchant,
        amount: avg,
        last: ordered.at(-1)!.transaction_date,
        category: ordered[0].category,
      };
    });
  const baseline = recurring.reduce((sum, row) => sum + row.amount, 0);
  return (
    <>
      <PageHeader
        eyebrow="Recurring"
        title="Know your baseline."
        description="Likely repeats are detected from merchant, amount, and timing. You decide what counts as fixed."
      />
      <div className="split-stats">
        <Card>
          <span>Likely monthly baseline</span>
          <strong>{money(baseline)}</strong>
          <small>Detected from your own history</small>
        </Card>
        <Card>
          <span>Recurring patterns</span>
          <strong>{recurring.length}</strong>
          <small>Requires at least two matching charges</small>
        </Card>
      </div>
      <Card>
        <div className="card-heading">
          <div>
            <span>RECURRING ACTIVITY</span>
            <h2>{recurring.length} detected patterns</h2>
          </div>
        </div>
        {recurring.length ? (
          <div className="recurring-table">
            <div className="rec-row header">
              <span>Merchant</span>
              <span>Expected</span>
              <span>Frequency</span>
              <span>Last charge</span>
              <span>Next charge</span>
              <span>Category</span>
              <span>Status</span>
            </div>
            {recurring.map((row) => (
              <div className="rec-row" key={row.merchant}>
                <span className="strong">{row.merchant}</span>
                <span>{money(row.amount)}</span>
                <span>Likely recurring</span>
                <span>{row.last}</span>
                <span>Estimate after more history</span>
                <span>{row.category}</span>
                <span className="pill fixed">Review</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="inline-empty">
            <Repeat2 size={22} />
            <strong>No recurring patterns yet</strong>
            <span>
              They will appear after Ember sees repeat charges across
              statements.
            </span>
          </div>
        )}
      </Card>
    </>
  );
}

function NetWorthPage({
  accounts,
  history,
}: {
  accounts: Account[];
  history: { date: string; value: number }[];
}) {
  const cash = accounts
    .filter((a) => ["CHECKING", "SAVINGS"].includes(a.type))
    .reduce((s, a) => s + a.current_balance, 0);
  const investments = accounts
    .filter((a) => ["BROKERAGE", "RETIREMENT"].includes(a.type))
    .reduce((s, a) => s + a.current_balance, 0);
  const liabilities = accounts
    .filter((a) => a.type === "CREDIT_CARD")
    .reduce((s, a) => s + Math.abs(a.current_balance), 0);
  const total = cash + investments - liabilities;
  const chartData = history;
  const change =
    chartData.length > 1 ? chartData.at(-1)!.value - chartData[0].value : 0;
  const changePercent =
    chartData.length > 1 && chartData[0].value
      ? (change / chartData[0].value) * 100
      : 0;
  return (
    <>
      <PageHeader
        eyebrow="Net worth"
        title={money(total)}
        description="Cash + investments + other assets − liabilities. History begins when you started using Ember."
      />
      <div className="worth-layout">
        <Card className="worth-chart">
          <div className="card-heading">
            <div>
              <span>NET WORTH OVER TIME</span>
              <h2>
                {chartData.length > 1
                  ? `${change >= 0 ? "Up" : "Down"} ${money(Math.abs(change))} since your first snapshot`
                  : "Add balance snapshots to build history"}
              </h2>
            </div>
            {chartData.length > 1 && (
              <span className="status-good">
                <ArrowUpRight size={14} /> {Math.abs(changePercent).toFixed(1)}%
              </span>
            )}
          </div>
          {chartData.length ? (
            <ResponsiveContainer width="100%" height={340}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="worthFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0" stopColor="#D99162" stopOpacity={0.28} />
                    <stop offset="1" stopColor="#D99162" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke="#EDF0EC" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip content={<ChartTip />} />
                <Area
                  type="monotone"
                  dataKey="value"
                  name="Net worth"
                  stroke="#D17F4D"
                  fill="url(#worthFill)"
                  strokeWidth={3}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="inline-empty">
              <PiggyBank size={22} />
              <strong>No snapshots yet</strong>
              <span>
                Manual assets create snapshots when you update their balances.
              </span>
            </div>
          )}
        </Card>
        <Card className="worth-breakdown">
          <span>BREAKDOWN</span>
          <h2>What you own and owe</h2>
          {[
            ["Cash", cash, "#183F35"],
            ["Investments", investments, "#D99162"],
            ["Liabilities", -liabilities, "#B45D51"],
          ].map(([label, value, color]) => (
            <div key={String(label)}>
              <i style={{ background: String(color) }} />
              <span>{label}</span>
              <strong className={Number(value) < 0 ? "negative" : ""}>
                {money(Number(value))}
              </strong>
            </div>
          ))}
          <hr />
          <div className="worth-total">
            <span>Net worth</span>
            <strong>{money(total)}</strong>
          </div>
        </Card>
      </div>
      <Card>
        <div className="card-heading">
          <div>
            <span>ACCOUNTS</span>
            <h2>Balance sources</h2>
          </div>
        </div>
        <div className="account-grid">
          {accounts.map((account) => (
            <button key={account.id}>
              <div className="account-logo">
                {account.institution.charAt(0) || account.name.charAt(0)}
              </div>
              <div>
                <strong>{account.name}</strong>
                <small>
                  {account.institution}
                  {account.last_four
                    ? ` ···· ${account.last_four}`
                    : " · manual balance"}
                </small>
              </div>
              <b>
                {account.type === "CREDIT_CARD" ? "−" : ""}
                {money(Math.abs(account.current_balance))}
              </b>
            </button>
          ))}
        </div>
      </Card>
    </>
  );
}

function ImportPage({
  accounts,
  onComplete,
}: {
  accounts: Account[];
  onComplete: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [account, setAccount] = useState(String(accounts[0]?.id || 1));
  const [sign, setSign] = useState("auto");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function upload() {
    if (!file) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("account_id", account);
    form.append("sign_convention", sign);
    form.append("file", file);
    try {
      const response = await fetch(`${API}/imports/preview`, {
        method: "POST",
        body: form,
      });
      if (!response.ok)
        throw new Error(
          (await response.json()).detail || "Could not parse this file",
        );
      setPreview(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Backend is not running");
    } finally {
      setBusy(false);
    }
  }
  async function commit() {
    if (!preview) return;
    setBusy(true);
    try {
      const response = await fetch(
        `${API}/imports/${preview.batch_id}/commit`,
        { method: "POST" },
      );
      if (!response.ok) throw new Error("Import failed");
      const result = await response.json();
      setPreview({ ...preview, ...result, committedDone: true });
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }
  if (!accounts.length)
    return (
      <>
        <PageHeader
          eyebrow="Transaction import"
          title="Create an account first."
          description="Each statement must be tied to an account so duplicates and transfers can be handled correctly."
        />
        <Card className="empty">
          <h2>No accounts yet</h2>
          <p>
            Open Settings and add a checking, savings, credit-card, or asset
            account before importing.
          </p>
        </Card>
      </>
    );
  return (
    <>
      <PageHeader
        eyebrow="Transaction import"
        title="Bring in a statement."
        description="PDFs and CSVs stay on your Mac. Review every normalized row and the duplicate check before saving."
      />
      <div className="import-steps">
        <span className="done">
          <b>1</b> Choose account
        </span>
        <i />
        <span className={preview ? "done" : ""}>
          <b>2</b> Verify preview
        </span>
        <i />
        <span className={preview?.committedDone ? "done" : ""}>
          <b>3</b> Commit
        </span>
      </div>
      {!preview ? (
        <Card className="import-card">
          <div className="form-grid">
            <label>
              Account
              <select
                value={account}
                onChange={(e) => setAccount(e.target.value)}
              >
                {accounts.map((a) => (
                  <option value={a.id} key={a.id}>
                    {a.name} · {a.institution}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Amount convention
              <select value={sign} onChange={(e) => setSign(e.target.value)}>
                <option value="auto">Auto detect</option>
                <option value="standard">Negative means money out</option>
                <option value="positive_outflow">
                  Positive means money out
                </option>
              </select>
            </label>
          </div>
          <button
            className={`drop-zone ${file ? "has-file" : ""}`}
            onClick={() => fileRef.current?.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.csv,application/pdf,text/csv"
              hidden
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <div>
              <Upload size={24} />
            </div>
            <strong>{file ? file.name : "Drop a PDF or CSV here"}</strong>
            <span>
              {file
                ? `${(file.size / 1024).toFixed(1)} KB · ready to inspect`
                : "Searchable PDF or CSV · up to 25 MB · contents are never logged"}
            </span>
          </button>
          {error && (
            <div className="import-error" role="alert">
              <strong>This statement was not imported.</strong>
              <p>{error}</p>
              <span>
                Confirm this is the full statement, not its cover or summary
                page. If preview still fails, export transactions as CSV from
                the same bank account and upload that file here.
              </span>
            </div>
          )}
          <button
            className="primary wide"
            disabled={!file || busy}
            onClick={upload}
          >
            {busy ? <Loading /> : "Extract and preview"}
          </button>
          <div className="privacy-note">
            <span>LOCAL ONLY</span>Chase checking, savings, and credit-card PDFs
            receive provider-specific parsing. Scanned PDFs are detected and
            require local OCR first.
          </div>
        </Card>
      ) : (
        <Card className="preview-card">
          <div className="import-summary">
            <div className="success-mark">
              <Check size={22} />
            </div>
            <div>
              <h2>
                {preview.committedDone
                  ? "Import complete"
                  : "Verify before importing"}
              </h2>
              <p>
                {preview.account} · {preview.total_rows} rows ·{" "}
                {preview.parse_report?.provider?.replaceAll("_", " ") || "CSV"}
              </p>
            </div>
            <div className="summary-numbers">
              <span>
                <strong>{preview.ready_to_import ?? preview.committed}</strong>{" "}
                new
              </span>
              <span>
                <strong>{preview.duplicates}</strong> duplicates skipped
              </span>
              <span>
                <strong>{preview.uncertain}</strong> need review
              </span>
            </div>
          </div>
          {preview.parse_report && (
            <div className={`parse-report ${preview.parse_report.confidence}`}>
              <strong>
                {preview.parse_report.confidence === "high"
                  ? "Recognized statement layout"
                  : "Manual verification required"}
              </strong>
              <span>
                {preview.parse_report.transactions_found} transactions extracted
                from {preview.parse_report.searchable_pages} searchable page
                {preview.parse_report.searchable_pages === 1
                  ? ""
                  : "s"} using {preview.parse_report.method}.
              </span>
              <small>
                Extracted totals: {money(preview.parse_report.outflows)} out ·{" "}
                {money(preview.parse_report.inflows)} in ·{" "}
                {money(preview.parse_report.net)} net. Reconcile these against
                the statement before committing.
              </small>
              {preview.parse_report.warnings?.map((warning: string) => (
                <small key={warning}>{warning}</small>
              ))}
            </div>
          )}
          {!!preview.cross_account_duplicates && !preview.committedDone && (
            <div className="import-warning" role="status">
              <strong>Possible wrong-account duplicate</strong>
              <p>
                {preview.cross_account_duplicates} row
                {preview.cross_account_duplicates === 1 ? "" : "s"} exactly
                match transactions already stored in another account. Confirm
                the selected account before importing. If this corrects an
                earlier mistake, import it and choose the account to keep under
                Review.
              </p>
            </div>
          )}
          {preview.preview?.length > 0 && (
            <div className="mini-preview detailed">
              <div className="preview-header">
                <span>Date</span>
                <span>Merchant</span>
                <b>Category · classification</b>
                <strong>Amount</strong>
              </div>
              {preview.preview.slice(0, 50).map((row, i) => (
                <div key={i}>
                  <small>{row.transaction_date}</small>
                  <span>{row.normalized_merchant}</span>
                  <b>
                    {row.category} · {row.classification.replaceAll("_", " ")}
                  </b>
                  <strong className={row.amount > 0 ? "positive" : ""}>
                    {row.amount > 0 ? "+" : "−"}
                    {money(Math.abs(row.amount))}
                  </strong>
                </div>
              ))}
            </div>
          )}
          <div className="commit-check">
            <Check size={16} />
            <span>
              By importing, I confirm the extracted dates, merchants, and
              amounts above look correct.
            </span>
          </div>
          <div className="preview-actions">
            <button className="secondary" onClick={() => setPreview(null)}>
              {preview.committedDone ? "Import another" : "Back"}
            </button>
            {!preview.committedDone && (
              <button className="primary" disabled={busy} onClick={commit}>
                {busy ? (
                  <Loading />
                ) : (
                  `Import ${preview.ready_to_import} transactions`
                )}
              </button>
            )}
          </div>
        </Card>
      )}
    </>
  );
}

function SettingsPage({
  accounts,
  onComplete,
}: {
  accounts: Account[];
  onComplete: () => void;
}) {
  const month = new Date().toISOString().slice(0, 7);
  const [postJob, setPostJob] = useState(new Date().toISOString().slice(0, 10));
  const [budget, setBudget] = useState({
    spending_target: "",
    savings_target: "",
    investment_target: "",
    savings_rate_target: "",
  });
  const [saveStatus, setSaveStatus] = useState("");
  const [showAccount, setShowAccount] = useState(false);
  const [editingAccountId, setEditingAccountId] = useState<number | null>(null);
  const [form, setForm] = useState({
    name: "",
    type: "CHECKING",
    institution: "",
    last_four: "",
    current_balance: "0",
    balance_mode: "TRANSACTION_DERIVED",
    active: true,
  });
  const restoreRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    Promise.all([
      fetch(`${API}/settings`).then((response) => response.json()),
      fetch(`${API}/budgets/${month}`).then((response) => response.json()),
    ])
      .then(([settings, currentBudget]) => {
        if (settings.post_job_start_date) {
          setPostJob(settings.post_job_start_date);
        }
        setBudget({
          spending_target: currentBudget.spending_target
            ? String(currentBudget.spending_target)
            : "",
          savings_target: currentBudget.savings_target
            ? String(currentBudget.savings_target)
            : "",
          investment_target: currentBudget.investment_target
            ? String(currentBudget.investment_target)
            : "",
          savings_rate_target: currentBudget.savings_rate_target
            ? String(currentBudget.savings_rate_target)
            : "",
        });
      })
      .catch(() => {
        setSaveStatus("Settings are unavailable while the API is offline");
      });
  }, [month]);
  async function saveDate() {
    try {
      const response = await fetch(
        `${API}/settings/post_job_start_date?value=${postJob}`,
        {
          method: "PUT",
        },
      );
      if (!response.ok) throw new Error();
      setSaveStatus("Comparison date saved");
    } catch {
      setSaveStatus("Could not save while the API is offline");
    }
  }
  async function saveBudget() {
    try {
      const response = await fetch(`${API}/budgets/${month}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          month,
          spending_target: Number(budget.spending_target || 0),
          savings_target: Number(budget.savings_target || 0),
          investment_target: Number(budget.investment_target || 0),
          savings_rate_target: Number(budget.savings_rate_target || 0),
          category_targets: {},
        }),
      });
      if (!response.ok) throw new Error();
      setSaveStatus("Monthly targets saved");
      onComplete();
    } catch {
      setSaveStatus("Could not save while the API is offline");
    }
  }
  function resetAccountForm() {
    setEditingAccountId(null);
    setShowAccount(false);
    setForm({
      name: "",
      type: "CHECKING",
      institution: "",
      last_four: "",
      current_balance: "0",
      balance_mode: "TRANSACTION_DERIVED",
      active: true,
    });
  }
  function startNewAccount() {
    resetAccountForm();
    setShowAccount(true);
  }
  function editAccount(account: Account) {
    setEditingAccountId(account.id);
    setForm({
      name: account.name,
      type: account.type,
      institution: account.institution,
      last_four: account.last_four || "",
      current_balance: String(account.current_balance),
      balance_mode: account.balance_mode,
      active: account.active,
    });
    setShowAccount(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  async function saveAccount() {
    if (!form.name) return;
    try {
      const response = await fetch(
        editingAccountId
          ? `${API}/accounts/${editingAccountId}`
          : `${API}/accounts`,
        {
          method: editingAccountId ? "PATCH" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            ...form,
            current_balance: Number(form.current_balance),
            last_four: form.last_four || null,
            save_snapshot: true,
          }),
        },
      );
      if (!response.ok) throw new Error();
      const message = editingAccountId ? "Account updated" : "Account added";
      resetAccountForm();
      setSaveStatus(message);
      onComplete();
    } catch {
      setSaveStatus("Could not save the account while the API is offline");
    }
  }
  async function restore(file: File | null) {
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const response = await fetch(`${API}/backup/restore`, {
        method: "POST",
        body,
      });
      if (!response.ok) throw new Error();
      window.location.reload();
    } catch {
      setSaveStatus("Could not restore this database backup");
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="Settings"
        title="Your system, your rules."
        description="Everything is local, editable, and exportable. No login, tracking, or bank credentials."
        action={
          <button
            className="primary"
            onClick={showAccount ? resetAccountForm : startNewAccount}
          >
            {showAccount ? <X size={16} /> : <Plus size={16} />}
            {showAccount ? "Close editor" : "Add account"}
          </button>
        }
      />
      {showAccount && (
        <Card className="account-form">
          <div className="card-heading">
            <div>
              <span>{editingAccountId ? "EDIT ACCOUNT" : "NEW ACCOUNT"}</span>
              <h2>
                {editingAccountId ? "Update account details" : "Add an account"}
              </h2>
            </div>
          </div>
          <div className="form-grid">
            <label>
              Account name
              <input
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Everyday checking"
              />
            </label>
            <label>
              Account type
              <select
                value={form.type}
                onChange={(e) =>
                  setForm({
                    ...form,
                    type: e.target.value,
                    balance_mode: [
                      "BROKERAGE",
                      "RETIREMENT",
                      "OTHER_ASSET",
                    ].includes(e.target.value)
                      ? "MANUAL"
                      : form.balance_mode,
                  })
                }
              >
                {[
                  "CHECKING",
                  "SAVINGS",
                  "CREDIT_CARD",
                  "BROKERAGE",
                  "RETIREMENT",
                  "OTHER_ASSET",
                ].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              Institution
              <input
                value={form.institution}
                onChange={(e) =>
                  setForm({ ...form, institution: e.target.value })
                }
                placeholder="Your bank"
              />
            </label>
            <label>
              Last four · optional
              <input
                maxLength={4}
                value={form.last_four}
                onChange={(e) =>
                  setForm({
                    ...form,
                    last_four: e.target.value.replace(/\D/g, ""),
                  })
                }
                placeholder="1234"
              />
            </label>
            <label>
              Current balance
              <input
                type="number"
                value={form.current_balance}
                onChange={(e) =>
                  setForm({ ...form, current_balance: e.target.value })
                }
              />
            </label>
            <label>
              Balance source
              <select
                value={form.balance_mode}
                onChange={(e) =>
                  setForm({ ...form, balance_mode: e.target.value })
                }
              >
                <option value="TRANSACTION_DERIVED">Transaction derived</option>
                <option value="MANUAL">Manual balance</option>
              </select>
            </label>
            <label className="account-active-toggle">
              <input
                type="checkbox"
                checked={form.active}
                onChange={(event) =>
                  setForm({ ...form, active: event.target.checked })
                }
              />
              <span>
                <strong>Include in Ember</strong>
                <small>Turn this off to archive the account.</small>
              </span>
            </label>
          </div>
          <div className="form-actions">
            <button className="secondary" onClick={resetAccountForm}>
              Cancel
            </button>
            <button className="primary" onClick={saveAccount}>
              {editingAccountId ? "Save changes" : "Save account"}
            </button>
          </div>
        </Card>
      )}
      <div className="settings-layout">
        <div>
          <Card className="setting-panel">
            <div className="card-heading">
              <div>
                <span>ACCOUNTS</span>
                <h2>{accounts.length} tracked accounts</h2>
              </div>
            </div>
            <div className="settings-accounts">
              {accounts.map((a) => (
                <div key={a.id}>
                  <div className="account-logo">
                    {a.institution.charAt(0) || a.name.charAt(0)}
                  </div>
                  <span>
                    <strong>{a.name}</strong>
                    <small>
                      {a.type.replaceAll("_", " ")} ·{" "}
                      {a.balance_mode === "MANUAL" ? "manual" : "derived"}
                      {!a.active ? " · archived" : ""}
                    </small>
                  </span>
                  <b>
                    {a.type === "CREDIT_CARD" ? "−" : ""}
                    {money(Math.abs(a.current_balance))}
                  </b>
                  <button
                    className="account-edit-button"
                    onClick={() => editAccount(a)}
                    aria-label={`Edit ${a.name}`}
                  >
                    <Pencil size={14} /> Edit
                  </button>
                </div>
              ))}
              {!accounts.length && (
                <div className="settings-empty">
                  No accounts yet. Add one above to begin.
                </div>
              )}
            </div>
          </Card>
          <Card className="setting-panel">
            <span>MONTHLY TARGETS · {month}</span>
            <h2>Set your broad budget</h2>
            <p>
              Leave a field at zero if you do not want it included. Targets
              never roll over automatically.
            </p>
            <div className="budget-form">
              {[
                ["Spending limit", "spending_target"],
                ["Savings target", "savings_target"],
                ["Investment target", "investment_target"],
                ["Savings-rate target", "savings_rate_target"],
              ].map(([label, key]) => (
                <label key={key}>
                  {label}
                  <input
                    type="number"
                    min="0"
                    max={key === "savings_rate_target" ? "100" : undefined}
                    value={budget[key as keyof typeof budget]}
                    onChange={(event) =>
                      setBudget({ ...budget, [key]: event.target.value })
                    }
                    placeholder="0"
                  />
                </label>
              ))}
            </div>
            <button className="primary small" onClick={saveBudget}>
              Save monthly targets
            </button>
          </Card>
        </div>
        <div>
          <Card className="setting-panel">
            <span>POST-JOB BOUNDARY</span>
            <h2>Comparison baseline</h2>
            <p>
              Budget recommendations prefer post-job data once there is enough
              history.
            </p>
            <label>
              Start date
              <input
                type="date"
                value={postJob}
                onChange={(e) => setPostJob(e.target.value)}
              />
            </label>
            <button className="primary small" onClick={saveDate}>
              Save date
            </button>
            {saveStatus && <small className="save-status">{saveStatus}</small>}
          </Card>
          <Card className="setting-panel">
            <span>LOCAL DATA</span>
            <h2>Backup & export</h2>
            <p>
              Your database lives in <code>backend/data</code>. Create a
              portable copy anytime.
            </p>
            <a className="secondary download" href={`${API}/backup`}>
              <Download size={16} /> Download database backup
            </a>
            <a
              className="secondary download"
              href={`${API}/export/transactions.csv`}
            >
              <Download size={16} /> Export transactions CSV
            </a>
            <input
              hidden
              ref={restoreRef}
              type="file"
              accept=".db,.sqlite,.sqlite3"
              onChange={(e) => restore(e.target.files?.[0] || null)}
            />
            <button
              className="secondary download"
              onClick={() => restoreRef.current?.click()}
            >
              <Upload size={16} /> Restore database backup
            </button>
          </Card>
          <Card className="setting-panel">
            <span>MANUAL ASSETS</span>
            <h2>
              {accounts.filter((a) => a.balance_mode === "MANUAL").length}{" "}
              manually tracked
            </h2>
            <p>Manual balance changes create a dated net-worth snapshot.</p>
            <button className="secondary" onClick={startNewAccount}>
              <Plus size={16} /> Add asset account
            </button>
          </Card>
        </div>
      </div>
    </>
  );
}

function TransactionDrawer({
  tx,
  onClose,
  onSave,
}: {
  tx: Transaction;
  onClose: () => void;
  onSave: (tx: Transaction) => void;
}) {
  const [category, setCategory] = useState(tx.category);
  const [classification, setClassification] = useState(tx.classification);
  const [merchant, setMerchant] = useState(tx.normalized_merchant);
  const [rule, setRule] = useState(false);
  const [saveError, setSaveError] = useState("");
  const categories = [
    "Housing",
    "Groceries",
    "Dining",
    "Bars & Nightlife",
    "Transportation",
    "Travel",
    "Shopping",
    "Entertainment",
    "Health & Fitness",
    "Subscriptions",
    "Gifts",
    "Miscellaneous",
    "Salary",
    "Refund",
    "Reimbursement",
    "Savings Transfer",
    "Investment Contribution",
    "Internal Transfer",
    "Credit Card Payment",
  ];
  const classes = [
    "EXPENSE",
    "INCOME",
    "TRANSFER",
    "CREDIT_CARD_PAYMENT",
    "SAVING",
    "INVESTMENT",
    "REFUND",
    "REIMBURSEMENT",
    "UNKNOWN",
  ];
  async function save() {
    const body = {
      category,
      classification,
      normalized_merchant: merchant,
      manually_reviewed: true,
      create_rule: rule,
    };
    try {
      const response = await fetch(`${API}/transactions/${tx.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error();
      onSave({ ...tx, ...body, confidence: 1 });
    } catch {
      setSaveError("Could not save while the API is offline");
    }
  }
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <button className="drawer-close" onClick={onClose}>
          <X size={20} />
        </button>
        <span className="eyebrow">Transaction detail</span>
        <h2>{tx.normalized_merchant}</h2>
        <strong className={`drawer-amount ${tx.amount > 0 ? "positive" : ""}`}>
          {tx.amount > 0 ? "+" : "−"}
          {money(Math.abs(tx.amount))}
        </strong>
        <p className="raw">{tx.raw_description}</p>
        <div className="explain">
          <strong>How this counts</strong>
          <p>
            {classification === "EXPENSE"
              ? "Included in spending and reduces monthly surplus."
              : classification === "INCOME"
                ? "Included in earned income and the savings-rate denominator."
                : classification === "REFUND" ||
                    classification === "REIMBURSEMENT"
                  ? "Offsets spending without inflating earned income."
                  : "Excluded from spending to prevent double counting money movement."}
          </p>
        </div>
        <label>
          Merchant name
          <input
            value={merchant}
            onChange={(e) => setMerchant(e.target.value)}
          />
        </label>
        <label>
          Classification
          <select
            value={classification}
            onChange={(e) => setClassification(e.target.value)}
          >
            {classes.map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          Category
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {categories.map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={rule}
            onChange={(e) => setRule(e.target.checked)}
          />
          <span>Always apply this choice to the exact description pattern</span>
        </label>
        {saveError && <p className="form-error">{saveError}</p>}
        <button className="primary wide" onClick={save}>
          Save correction
        </button>
      </aside>
    </div>
  );
}

export default function FinanceDashboard() {
  const [page, setPage] = useState("Home");
  const [period, setPeriod] = useState("this_month");
  const [mobile, setMobile] = useState(false);
  const [dashboard, setDashboard] = useState<Dashboard>(EMPTY_DASHBOARD);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [selected, setSelected] = useState<Transaction | null>(null);
  const [filter, setFilter] = useState("");
  const [online, setOnline] = useState(false);
  const [loaded, setLoaded] = useState(false);
  async function refresh() {
    try {
      const data = await fetchFinanceData(period);
      setDashboard(data.dashboard);
      setTransactions(data.transactions);
      setAccounts(data.accounts);
      setOnline(true);
    } catch {
      setOnline(false);
    } finally {
      setLoaded(true);
    }
  }
  useEffect(() => {
    let active = true;
    fetchFinanceData(period)
      .then((data) => {
        if (!active) return;
        setDashboard(data.dashboard);
        setTransactions(data.transactions);
        setAccounts(data.accounts);
        setOnline(true);
      })
      .catch(() => {
        if (active) setOnline(false);
      })
      .finally(() => {
        if (active) setLoaded(true);
      });
    return () => {
      active = false;
    };
  }, [period]);
  function navigate(next: string) {
    setPage(next);
    setMobile(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  function filterTo(value: string) {
    setFilter(value);
    navigate("Transactions");
  }
  function saveTransaction(updated: Transaction) {
    setTransactions((rows) =>
      rows.map((row) => (row.id === updated.id ? updated : row)),
    );
    setSelected(null);
    refresh();
  }
  async function saveReviewDecision(
    tx: Transaction,
    classification: string,
    category: string,
  ) {
    const updated = {
      ...tx,
      classification,
      category,
      manually_reviewed: true,
      confidence: 1,
    };
    setTransactions((rows) =>
      rows.map((row) => (row.id === tx.id ? updated : row)),
    );
    try {
      const shouldLearn = !/ZELLE|VENMO|CASH\s*APP/i.test(tx.raw_description);
      await fetch(`${API}/transactions/${tx.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          classification,
          category,
          manually_reviewed: true,
          create_rule: shouldLearn,
        }),
      });
      await refresh();
    } catch {
      await refresh();
    }
  }
  async function resolveDuplicateGroup(
    duplicateTransactions: Transaction[],
    keepAccountId: number,
  ) {
    const response = await fetch(`${API}/duplicates/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        transaction_ids: duplicateTransactions.map(
          (transaction) => transaction.id,
        ),
        keep_account_id: keepAccountId,
      }),
    });
    if (!response.ok) throw new Error("Could not resolve duplicates");
    await refresh();
  }
  let content: ReactNode;
  if (!loaded) content = <Loading />;
  else if (page === "Home")
    content = (
      <HomePage
        accounts={accounts}
        transactions={transactions}
        reviewCount={dashboard.review_count}
        onNavigate={navigate}
      />
    );
  else if (page === "Overview")
    content = (
      <Overview
        data={dashboard}
        transactions={transactions}
        accounts={accounts}
        onNavigate={navigate}
        onFilter={filterTo}
        onSelect={setSelected}
        period={period}
        onPeriodChange={setPeriod}
      />
    );
  else if (page === "Transactions")
    content = (
      <TransactionsPage
        key={filter}
        transactions={transactions}
        accounts={accounts}
        initialFilter={filter}
        onSelect={setSelected}
      />
    );
  else if (page === "Spending")
    content = (
      <SpendingPage
        data={dashboard}
        transactions={transactions}
        onFilter={filterTo}
        period={period}
        onPeriodChange={setPeriod}
      />
    );
  else if (page === "Review")
    content = (
      <ReviewPage
        rows={transactions}
        accounts={accounts}
        onReview={saveReviewDecision}
        onResolveDuplicates={resolveDuplicateGroup}
      />
    );
  else if (page === "Compare")
    content = <ComparePage transactions={transactions} onFilter={filterTo} />;
  else if (page === "Monthly Report")
    content = (
      <MonthlyReportPage
        data={dashboard}
        transactions={transactions}
        onFilter={filterTo}
        period={period}
        onPeriodChange={setPeriod}
      />
    );
  else if (page === "FIRE Plan")
    content = (
      <FirePage data={dashboard} period={period} onPeriodChange={setPeriod} />
    );
  else if (page === "Recurring")
    content = <RecurringPage transactions={transactions} />;
  else if (page === "Net Worth")
    content = (
      <NetWorthPage accounts={accounts} history={dashboard.net_worth} />
    );
  else if (page === "Import")
    content = <ImportPage accounts={accounts} onComplete={refresh} />;
  else content = <SettingsPage accounts={accounts} onComplete={refresh} />;
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <div className="brand">
          <MiniLogo />
          <div>
            <strong>Ember</strong>
            <span>Personal finance</span>
          </div>
          <button onClick={() => setMobile(false)}>
            <X size={18} />
          </button>
        </div>
        <nav>
          {nav.map(([label, Icon]) => (
            <button
              key={label}
              className={page === label ? "active" : ""}
              onClick={() => navigate(label)}
            >
              <Icon size={18} />
              <span>{label}</span>
              {label === "Review" && dashboard.review_count > 0 && (
                <b>{dashboard.review_count}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="privacy">
            <span />
            <div>
              <strong>Private by design</strong>
              <small>Stored on this Mac</small>
            </div>
          </div>
          <p>EMBER · LOCAL EDITION</p>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setMobile(true)}>
            <Menu size={20} />
          </button>
          <div className="connection">
            <span className={online ? "online" : ""} />
            {online
              ? "Local database connected"
              : "API offline · run the local start script"}
          </div>
          <div className="top-actions">
            <div className="avatar">EF</div>
          </div>
        </header>
        <div className="content">
          {content}
          <footer>
            <MiniLogo />
            <span>Built for clarity. Your data never leaves this Mac.</span>
          </footer>
        </div>
      </main>
      {selected && (
        <TransactionDrawer
          tx={selected}
          onClose={() => setSelected(null)}
          onSave={saveTransaction}
        />
      )}
    </div>
  );
}
