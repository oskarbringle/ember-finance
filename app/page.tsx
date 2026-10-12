"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
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
  ArrowDownRight,
  ArrowLeftRight,
  ArrowUpRight,
  BarChart3,
  Check,
  ChevronDown,
  ChevronRight,
  CircleDollarSign,
  Gauge,
  Landmark,
  Menu,
  PiggyBank,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UploadCloud,
  WalletCards,
  X,
} from "lucide-react";
import {
  Card,
  ChartTooltip,
  EmptyState,
  Loading,
  MetricCard,
  MiniLogo,
  PageHeader,
} from "./components/dashboard-ui";
import {
  API_BASE_URL,
  CHART_COLORS,
  EMPTY_DATA,
  fetchFinanceData,
  formatCurrency,
  monthLabel,
  type ExpenseEntry,
  type FinanceData,
  type FinanceFilters,
  type ImportPreview,
  type Metrics,
} from "./lib/finance";

type PageName =
  "Overview" | "Spending" | "Income" | "Net Worth" | "Compare" | "Import";

const NAV_ITEMS: [PageName, typeof Gauge][] = [
  ["Overview", Gauge],
  ["Spending", WalletCards],
  ["Income", CircleDollarSign],
  ["Net Worth", Landmark],
  ["Compare", ArrowLeftRight],
  ["Import", UploadCloud],
];

const DEFAULT_FILTERS: FinanceFilters = {
  period: "this_month",
  startMonth: "",
  endMonth: "",
  includeWork: false,
  includeOneTime: true,
  includeTravel: true,
};

function selectedPeriodLabel(data: FinanceData) {
  const months = data.metadata.selected_months;
  if (!months.length) return "No period selected";
  if (months.length === 1) return monthLabel(months[0]);
  return `${monthLabel(months[0], true)} – ${monthLabel(months.at(-1) || "", true)}`;
}

function FilterBar({
  filters,
  setFilters,
  months,
}: {
  filters: FinanceFilters;
  setFilters: (filters: FinanceFilters) => void;
  months: string[];
}) {
  const update = <K extends keyof FinanceFilters>(
    key: K,
    value: FinanceFilters[K],
  ) => setFilters({ ...filters, [key]: value });
  return (
    <div className="filter-bar">
      <select
        aria-label="Time period"
        value={filters.period}
        onChange={(event) => {
          const period = event.target.value as FinanceFilters["period"];
          setFilters({
            ...filters,
            period,
            startMonth: filters.startMonth || months[0] || "",
            endMonth: filters.endMonth || months.at(-1) || "",
          });
        }}
      >
        <option value="this_month">This Month</option>
        <option value="last_month">Last Month</option>
        <option value="last_3_months">Last 3 Months</option>
        <option value="all_time">All Time</option>
        <option value="custom">Custom Month Range</option>
      </select>
      {filters.period === "custom" && (
        <div className="month-range">
          <select
            value={filters.startMonth}
            onChange={(event) => update("startMonth", event.target.value)}
          >
            {months.map((month) => (
              <option key={month} value={month}>
                {monthLabel(month)}
              </option>
            ))}
          </select>
          <span>to</span>
          <select
            value={filters.endMonth}
            onChange={(event) => update("endMonth", event.target.value)}
          >
            {months.map((month) => (
              <option key={month} value={month}>
                {monthLabel(month)}
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="view-toggles" aria-label="Expense visibility filters">
        <button
          className={filters.includeWork ? "active" : ""}
          onClick={() => update("includeWork", !filters.includeWork)}
        >
          <Check size={13} /> Work reimbursable
        </button>
        <button
          className={filters.includeOneTime ? "active" : ""}
          onClick={() => update("includeOneTime", !filters.includeOneTime)}
        >
          <Check size={13} /> One-time
        </button>
        <button
          className={filters.includeTravel ? "active" : ""}
          onClick={() => update("includeTravel", !filters.includeTravel)}
        >
          <Check size={13} /> Personal travel
        </button>
      </div>
    </div>
  );
}

function ChartHeader({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: ReactNode;
}) {
  return (
    <div className="chart-header">
      <div>
        <h2>{title}</h2>
        <p>{detail}</p>
      </div>
      {action}
    </div>
  );
}

function OverviewPage({
  data,
  onImport,
}: {
  data: FinanceData;
  onImport: () => void;
}) {
  if (!data.metadata.available_months.length)
    return <EmptyState onImport={onImport} />;
  const metrics = data.metrics;
  const detail = selectedPeriodLabel(data);
  const latest = data.monthly.at(-1);
  const wealthTooltip =
    "An estimate of how much new wealth your normal income and spending created this month, excluding internal transfers, reimbursements, and one-off income.";
  const rateTooltip =
    "Monthly Wealth Added ÷ (Recurring Earned Income + Payroll Retirement Contributions). It estimates how much of your normal earning power became new wealth.";
  return (
    <>
      <PageHeader
        eyebrow="Financial overview"
        title="Your money, made legible."
        description={`A compact view of income, lifestyle cost, investing, and wealth creation for ${detail}.`}
      />
      <div className="metric-grid">
        <MetricCard
          label="Total income"
          value={formatCurrency(metrics.total_income, true)}
          detail="All cash inflow"
          icon={CircleDollarSign}
        />
        <MetricCard
          label="Recurring earned income"
          value={formatCurrency(metrics.recurring_income, true)}
          detail="Paycheck + side income"
          icon={RefreshCw}
        />
        <MetricCard
          label="Total spending"
          value={formatCurrency(metrics.total_spending, true)}
          detail="All recorded expenses"
          icon={WalletCards}
        />
        <MetricCard
          label="Personal spending"
          value={formatCurrency(metrics.personal_spending, true)}
          detail="Excludes reimbursable work"
          icon={Gauge}
        />
        <MetricCard
          label="Core spending"
          value={formatCurrency(metrics.core_spending, true)}
          detail="Normal lifestyle baseline"
          icon={ShieldCheck}
          accent
        />
        <MetricCard
          label="Cash-flow surplus"
          value={formatCurrency(metrics.cash_flow_surplus, true)}
          detail="Inflow minus personal spend"
          icon={TrendingUp}
        />
        <MetricCard
          label="Retirement investing"
          value={formatCurrency(metrics.retirement_investing, true)}
          detail="401(k), HSA and similar"
          icon={Landmark}
        />
        <MetricCard
          label="Other investing"
          value={formatCurrency(metrics.other_investing, true)}
          detail="Roth and brokerage"
          icon={BarChart3}
        />
        <MetricCard
          label="Monthly Wealth Added"
          value={formatCurrency(metrics.monthly_wealth_added, true)}
          detail="Estimated new wealth"
          icon={PiggyBank}
          tooltip={wealthTooltip}
          accent
        />
        <MetricCard
          label="Wealth-building rate"
          value={`${metrics.wealth_building_rate.toFixed(1)}%`}
          detail="Share of earning power saved"
          icon={Sparkles}
          tooltip={rateTooltip}
        />
        <MetricCard
          label="Current net worth"
          value={formatCurrency(data.current_net_worth, true)}
          detail="Latest workbook snapshot"
          icon={Landmark}
        />
      </div>

      <Card className="core-spotlight">
        <div>
          <span className="eyebrow">Core spending</span>
          <h2>What does normal life actually cost?</h2>
          <p>
            Reimbursable work, one-time purchases, and personal travel remain
            visible elsewhere, but do not distort this baseline.
          </p>
        </div>
        <div className="spotlight-number">
          <small>Current month</small>
          <strong>{formatCurrency(latest?.core_spending || 0)}</strong>
        </div>
        <div className="spotlight-number">
          <small>Selected-period average</small>
          <strong>{formatCurrency(data.average_core_spending)}</strong>
        </div>
      </Card>

      <div className="two-column">
        <Card className="chart-card">
          <ChartHeader
            title="Income, spending & wealth added"
            detail="The three numbers that define each month."
          />
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={data.monthly} barGap={4}>
              <CartesianGrid vertical={false} stroke="#edf0ec" />
              <XAxis
                dataKey="month"
                tickFormatter={(value) => monthLabel(value, true)}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(value) => `$${Math.round(value / 1000)}k`}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              <Bar
                dataKey="recurring_income"
                name="Recurring income"
                fill="#244b42"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="personal_spending"
                name="Personal spending"
                fill="#d48652"
                radius={[4, 4, 0, 0]}
              />
              <Bar
                dataKey="monthly_wealth_added"
                name="Wealth added"
                fill="#d9ae55"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card className="chart-card">
          <ChartHeader
            title="Wealth-building rate"
            detail="How efficiently normal earning power becomes wealth."
          />
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={data.monthly}>
              <CartesianGrid vertical={false} stroke="#edf0ec" />
              <XAxis
                dataKey="month"
                tickFormatter={(value) => monthLabel(value, true)}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(value) => `${value}%`}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip percent />} />
              <Line
                type="monotone"
                dataKey="wealth_building_rate"
                name="Wealth-building rate"
                stroke="#244b42"
                strokeWidth={3}
                dot={{ r: 4, fill: "#244b42" }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <Card className="insights-card">
        <ChartHeader
          title="What changed"
          detail="Deterministic observations from your imported workbook."
        />
        <div className="insight-list">
          {data.insights.map((insight, index) => (
            <div key={insight}>
              <span>{index + 1}</span>
              <p>{insight}</p>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

function CategoryDrawer({
  category,
  expenses,
  onClose,
}: {
  category: string;
  expenses: ExpenseEntry[];
  onClose: () => void;
}) {
  const rows = expenses.filter((row) => row.category === category);
  return (
    <div className="drawer-backdrop" onMouseDown={onClose}>
      <aside
        className="detail-drawer"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button
          className="icon-button drawer-close"
          onClick={onClose}
          aria-label="Close category details"
        >
          <X size={19} />
        </button>
        <span className="eyebrow">Category detail</span>
        <h2>{category}</h2>
        <strong className="drawer-total">
          {formatCurrency(rows.reduce((sum, row) => sum + row.amount, 0))}
        </strong>
        <p>{rows.length} entries in the selected view</p>
        <div className="drawer-rows">
          {rows.map((row) => (
            <div key={row.id}>
              <div>
                <strong>{row.description}</strong>
                <small>
                  {monthLabel(row.month)}
                  {row.expense_tag ? ` · ${row.expense_tag}` : ""}
                </small>
              </div>
              <b>{formatCurrency(row.amount)}</b>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}

function SpendingPage({ data }: { data: FinanceData }) {
  const [drilldown, setDrilldown] = useState<string | null>(null);
  const [trendMetric, setTrendMetric] = useState<
    "total_spending" | "personal_spending" | "core_spending"
  >("core_spending");
  const [trendCategory, setTrendCategory] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const selectedTrendCategory =
    trendCategory || data.categories[0]?.category || "";
  return (
    <>
      <PageHeader
        eyebrow="Spending analysis"
        title="See the shape of your spending."
        description="Move from category-level patterns to individual spreadsheet entries in one click."
      />
      <div className="two-column spending-top">
        <Card className="chart-card">
          <ChartHeader
            title="Spending by category"
            detail="Click a segment to inspect its entries."
          />
          <ResponsiveContainer width="100%" height={340}>
            <PieChart>
              <Pie
                data={data.categories}
                dataKey="value"
                nameKey="category"
                innerRadius={78}
                outerRadius={122}
                paddingAngle={2}
                onClick={(entry) => setDrilldown(String(entry.category))}
              >
                {data.categories.map((row, index) => (
                  <Cell
                    key={row.category}
                    fill={CHART_COLORS[index % CHART_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip content={<ChartTooltip />} />
              <Legend verticalAlign="bottom" />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card className="chart-card">
          <ChartHeader
            title="Category ranking"
            detail="Largest spending areas, ordered by total."
          />
          <ResponsiveContainer width="100%" height={340}>
            <BarChart
              data={data.categories.slice(0, 10)}
              layout="vertical"
              margin={{ left: 24 }}
            >
              <CartesianGrid horizontal={false} stroke="#edf0ec" />
              <XAxis
                type="number"
                tickFormatter={(value) => `$${value}`}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                dataKey="category"
                type="category"
                width={120}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <Bar
                dataKey="value"
                name="Spending"
                fill="#244b42"
                radius={[0, 5, 5, 0]}
                onClick={(entry) => setDrilldown(String(entry.category))}
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <div className="two-column">
        <Card className="chart-card">
          <ChartHeader
            title="Monthly spending trend"
            detail="Switch between total, personal, and normal lifestyle cost."
            action={
              <div className="segmented">
                {(
                  [
                    "total_spending",
                    "personal_spending",
                    "core_spending",
                  ] as const
                ).map((metric) => (
                  <button
                    key={metric}
                    className={trendMetric === metric ? "active" : ""}
                    onClick={() => setTrendMetric(metric)}
                  >
                    {metric.split("_")[0]}
                  </button>
                ))}
              </div>
            }
          />
          <ResponsiveContainer width="100%" height={290}>
            <LineChart data={data.monthly}>
              <CartesianGrid vertical={false} stroke="#edf0ec" />
              <XAxis
                dataKey="month"
                tickFormatter={(value) => monthLabel(value, true)}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(value) => `$${value}`}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <Line
                type="monotone"
                dataKey={trendMetric}
                name={trendMetric.replaceAll("_", " ")}
                stroke="#d48652"
                strokeWidth={3}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card className="chart-card">
          <ChartHeader
            title="Category trend"
            detail="Follow one category across every imported month."
            action={
              <select
                value={selectedTrendCategory}
                onChange={(event) => setTrendCategory(event.target.value)}
              >
                {data.categories.map((row) => (
                  <option key={row.category}>{row.category}</option>
                ))}
              </select>
            }
          />
          <ResponsiveContainer width="100%" height={290}>
            <AreaChart data={data.category_trends}>
              <defs>
                <linearGradient id="categoryFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#668b80" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#668b80" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid vertical={false} stroke="#edf0ec" />
              <XAxis
                dataKey="month"
                tickFormatter={(value) => monthLabel(value, true)}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(value) => `$${value}`}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="monotone"
                dataKey={selectedTrendCategory}
                name={selectedTrendCategory}
                stroke="#244b42"
                strokeWidth={3}
                fill="url(#categoryFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <Card className="breakdown-card">
        <ChartHeader
          title="Spending breakdown"
          detail="Expand any category to see its source entries."
        />
        <div className="breakdown-table">
          <div className="breakdown-head">
            <span>Category</span>
            <span>Total</span>
            <span>% of spending</span>
            <span>Entries</span>
          </div>
          {data.categories.map((row) => (
            <div key={row.category} className="breakdown-group">
              <button
                onClick={() =>
                  setExpanded(expanded === row.category ? null : row.category)
                }
              >
                <span>
                  {expanded === row.category ? (
                    <ChevronDown size={16} />
                  ) : (
                    <ChevronRight size={16} />
                  )}
                  <i
                    style={{
                      background:
                        CHART_COLORS[
                          data.categories.indexOf(row) % CHART_COLORS.length
                        ],
                    }}
                  />
                  {row.category}
                </span>
                <strong>{formatCurrency(row.value)}</strong>
                <span>{row.percentage.toFixed(1)}%</span>
                <span>{row.count}</span>
              </button>
              {expanded === row.category && (
                <div className="expanded-rows">
                  {data.expenses
                    .filter((entry) => entry.category === row.category)
                    .map((entry) => (
                      <div key={entry.id}>
                        <span>
                          {entry.description}
                          <small>
                            {monthLabel(entry.month)}
                            {entry.expense_tag ? ` · ${entry.expense_tag}` : ""}
                          </small>
                        </span>
                        <strong>{formatCurrency(entry.amount)}</strong>
                      </div>
                    ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>
      {drilldown && (
        <CategoryDrawer
          category={drilldown}
          expenses={data.expenses}
          onClose={() => setDrilldown(null)}
        />
      )}
    </>
  );
}

function IncomePage({ data }: { data: FinanceData }) {
  const byClass = Object.entries(
    data.income.reduce<Record<string, number>>(
      (result, row) => ({
        ...result,
        [row.income_class]: (result[row.income_class] || 0) + row.amount,
      }),
      {},
    ),
  ).map(([name, value]) => ({ name, value }));
  return (
    <>
      <PageHeader
        eyebrow="Income & investing"
        title="Trace earning power into wealth."
        description="Income and contributions stay separate from internal movement between your own accounts."
      />
      <div className="metric-grid compact-four">
        <MetricCard
          label="Recurring earned income"
          value={formatCurrency(data.metrics.recurring_income)}
          detail="Paycheck + side income"
          icon={RefreshCw}
        />
        <MetricCard
          label="Total cash inflow"
          value={formatCurrency(data.metrics.total_income)}
          detail="Includes irregular income"
          icon={CircleDollarSign}
        />
        <MetricCard
          label="Retirement investing"
          value={formatCurrency(data.metrics.retirement_investing)}
          detail="Payroll-oriented accounts"
          icon={Landmark}
        />
        <MetricCard
          label="Other investing"
          value={formatCurrency(data.metrics.other_investing)}
          detail="Roth + taxable investing"
          icon={TrendingUp}
        />
      </div>
      <div className="two-column">
        <Card className="chart-card">
          <ChartHeader
            title="Income mix"
            detail="Every income class in the selected period."
          />
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={byClass}>
              <CartesianGrid vertical={false} stroke="#edf0ec" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} />
              <YAxis
                tickFormatter={(value) => `$${value}`}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <Bar
                dataKey="value"
                name="Income"
                fill="#244b42"
                radius={[5, 5, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card className="chart-card">
          <ChartHeader
            title="Investment contributions"
            detail="Internal transfers are deliberately absent."
          />
          <div className="flow-list">
            {data.wealth_flows
              .filter((row) => row.flow_class !== "Internal Transfer")
              .map((row) => (
                <div key={row.id}>
                  <span>
                    <strong>{row.destination}</strong>
                    <small>
                      {row.flow_class} · {monthLabel(row.month)}
                    </small>
                  </span>
                  <b>{formatCurrency(row.amount)}</b>
                </div>
              ))}
          </div>
          {!!data.metrics.internal_transfers && (
            <div className="transfer-note">
              <ArrowLeftRight size={16} />
              <span>
                {formatCurrency(data.metrics.internal_transfers)} moved
                internally and was excluded from income, spending, investing,
                and wealth creation.
              </span>
            </div>
          )}
        </Card>
      </div>
      <Card className="entries-card">
        <ChartHeader
          title="Income entries"
          detail="Exactly as organized in the workbook."
        />
        <div className="simple-table">
          <div className="simple-head">
            <span>Description</span>
            <span>Class</span>
            <span>Month</span>
            <span>Amount</span>
          </div>
          {data.income.map((row) => (
            <div key={row.id}>
              <strong>{row.description}</strong>
              <span>{row.income_class}</span>
              <span>{monthLabel(row.month)}</span>
              <b>{formatCurrency(row.amount)}</b>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

function NetWorthPage({ data }: { data: FinanceData }) {
  return (
    <>
      <PageHeader
        eyebrow="Net worth"
        title={formatCurrency(data.current_net_worth)}
        description="Your latest saved workbook snapshot, with history beginning when you started tracking."
      />
      <div className="composition-grid">
        {data.net_worth_composition.map((row, index) => (
          <Card key={row.group} className="composition-card">
            <i
              style={{ background: CHART_COLORS[index % CHART_COLORS.length] }}
            />
            <span>{row.group}</span>
            <strong>{formatCurrency(row.value)}</strong>
          </Card>
        ))}
      </div>
      <div className="two-column net-worth-charts">
        <Card className="chart-card">
          <ChartHeader
            title="Net-worth history"
            detail="One point for each unique workbook snapshot date."
          />
          <ResponsiveContainer width="100%" height={330}>
            <LineChart data={data.net_worth}>
              <CartesianGrid vertical={false} stroke="#edf0ec" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} />
              <YAxis
                tickFormatter={(value) => `$${Math.round(value / 1000)}k`}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <Line
                type="monotone"
                dataKey="total"
                name="Net worth"
                stroke="#244b42"
                strokeWidth={3}
                dot={{ fill: "#244b42", r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card className="chart-card">
          <ChartHeader
            title="Composition over time"
            detail="Cash, taxable investments, and retirement accounts."
          />
          <ResponsiveContainer width="100%" height={330}>
            <AreaChart data={data.net_worth}>
              <CartesianGrid vertical={false} stroke="#edf0ec" />
              <XAxis dataKey="date" axisLine={false} tickLine={false} />
              <YAxis
                tickFormatter={(value) => `$${Math.round(value / 1000)}k`}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              {["Cash", "Taxable Investments", "Roth IRA", "HSA", "401(k)"].map(
                (group, index) => (
                  <Area
                    key={group}
                    type="monotone"
                    dataKey={group}
                    stackId="worth"
                    fill={CHART_COLORS[index]}
                    stroke={CHART_COLORS[index]}
                  />
                ),
              )}
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <Card className="entries-card">
        <ChartHeader
          title="Account balances"
          detail="Accounts from the latest Networth tab snapshot."
        />
        <div className="simple-table account-table">
          <div className="simple-head">
            <span>Account</span>
            <span>Type</span>
            <span>Group</span>
            <span>Balance</span>
          </div>
          {data.net_worth_accounts.map((row) => (
            <div key={row.account}>
              <strong>{row.account}</strong>
              <span>{row.account_type}</span>
              <span>{row.group}</span>
              <b>{formatCurrency(row.value)}</b>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

function deltaTone(value: number) {
  if (Math.abs(value) < 0.005) return "neutral";
  return value > 0 ? "up" : "down";
}

function ComparePage({ data }: { data: FinanceData }) {
  const months = data.metadata.available_months;
  const [monthA, setMonthA] = useState("");
  const [monthB, setMonthB] = useState("");
  const selectedMonthA = monthA || months.at(-1) || "";
  const selectedMonthB = monthB || months.at(-2) || months.at(-1) || "";
  const a = data.monthly.find((row) => row.month === selectedMonthA);
  const b = data.monthly.find((row) => row.month === selectedMonthB);
  const metricRows: [string, keyof Metrics, boolean][] = [
    ["Recurring income", "recurring_income", false],
    ["Total spending", "total_spending", false],
    ["Personal spending", "personal_spending", false],
    ["Core spending", "core_spending", false],
    ["Monthly Wealth Added", "monthly_wealth_added", false],
    ["Wealth-building rate", "wealth_building_rate", true],
  ];
  const trendA =
    data.category_trends.find((row) => row.month === selectedMonthA) || {};
  const trendB =
    data.category_trends.find((row) => row.month === selectedMonthB) || {};
  const categories = [
    ...new Set([...Object.keys(trendA), ...Object.keys(trendB)]),
  ]
    .filter((key) => key !== "month")
    .map((category) => ({
      category,
      current: Number(trendA[category] || 0),
      prior: Number(trendB[category] || 0),
    }))
    .sort((x, y) => y.current - x.current);
  return (
    <>
      <PageHeader
        eyebrow="Month comparison"
        title="See what materially changed."
        description="A restrained side-by-side view of cash flow, lifestyle cost, investing, and category movement."
        action={
          <div className="compare-selectors">
            <select
              value={selectedMonthA}
              onChange={(event) => setMonthA(event.target.value)}
            >
              {months.map((month) => (
                <option key={month} value={month}>
                  {monthLabel(month)}
                </option>
              ))}
            </select>
            <span>vs</span>
            <select
              value={selectedMonthB}
              onChange={(event) => setMonthB(event.target.value)}
            >
              {months.map((month) => (
                <option key={month} value={month}>
                  {monthLabel(month)}
                </option>
              ))}
            </select>
          </div>
        }
      />
      <Card className="comparison-card">
        <div className="comparison-head">
          <span>Metric</span>
          <span>{monthLabel(selectedMonthA)}</span>
          <span>{monthLabel(selectedMonthB)}</span>
          <span>Change</span>
        </div>
        {metricRows.map(([label, key, percent]) => {
          const current = (a?.[key] as number) || 0;
          const prior = (b?.[key] as number) || 0;
          const delta = current - prior;
          return (
            <div className="comparison-row" key={key}>
              <strong>{label}</strong>
              <span>
                {percent ? `${current.toFixed(1)}%` : formatCurrency(current)}
              </span>
              <span>
                {percent ? `${prior.toFixed(1)}%` : formatCurrency(prior)}
              </span>
              <b className={deltaTone(delta)}>
                {delta >= 0 ? (
                  <ArrowUpRight size={14} />
                ) : (
                  <ArrowDownRight size={14} />
                )}
                {percent
                  ? `${Math.abs(delta).toFixed(1)} pts`
                  : formatCurrency(Math.abs(delta))}
              </b>
            </div>
          );
        })}
      </Card>
      <Card className="comparison-card category-comparison">
        <ChartHeader
          title="Category-level change"
          detail="Current month total and difference from the comparison month."
        />
        <div className="comparison-head">
          <span>Category</span>
          <span>Current</span>
          <span>Previous</span>
          <span>Change</span>
        </div>
        {categories.map((row) => {
          const delta = row.current - row.prior;
          return (
            <div className="comparison-row" key={row.category}>
              <strong>{row.category}</strong>
              <span>{formatCurrency(row.current)}</span>
              <span>{formatCurrency(row.prior)}</span>
              <b className={deltaTone(-delta)}>
                {delta > 0 ? "+" : "−"}
                {formatCurrency(Math.abs(delta))}
              </b>
            </div>
          );
        })}
      </Card>
    </>
  );
}

function ImportPage({ onImported }: { onImported: () => Promise<void> }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function previewFile(file?: File) {
    if (!file) return;
    setBusy(true);
    setError("");
    setPreview(null);
    const form = new FormData();
    form.append("file", file);
    try {
      const response = await fetch(`${API_BASE_URL}/imports/preview`, {
        method: "POST",
        body: form,
      });
      const body = await response.json();
      if (!response.ok)
        throw new Error(body.detail || "Could not read workbook");
      setPreview(body as ImportPreview);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Could not read workbook",
      );
    } finally {
      setBusy(false);
    }
  }
  async function replaceData() {
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/imports/${preview.token}/replace`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ replace_current_data: true }),
        },
      );
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Import failed");
      await onImported();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Import failed");
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeader
        eyebrow="Spreadsheet import"
        title="Update the dashboard in one step."
        description="Your workbook remains the source of truth. Re-importing replaces monthly data instead of creating duplicates."
      />
      <Card className="import-card">
        <div
          className="drop-zone"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            previewFile(event.dataTransfer.files[0]);
          }}
        >
          <div className="upload-icon">
            <UploadCloud size={26} />
          </div>
          <h2>Drop your budgeting spreadsheet here</h2>
          <p>Excel .xlsx · month tabs are detected automatically</p>
          <button
            className="primary-button"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
          >
            {busy ? "Reading workbook…" : "Choose Excel File"}
          </button>
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx"
            hidden
            onChange={(event) => previewFile(event.target.files?.[0])}
          />
        </div>
        {error && <div className="error-banner">{error}</div>}
        {preview && (
          <div className="import-preview">
            <div className="preview-title">
              <div>
                <span className="eyebrow">Import preview</span>
                <h2>{preview.workbook_name}</h2>
              </div>
              <span
                className={
                  preview.can_import ? "status-ready" : "status-blocked"
                }
              >
                {preview.can_import ? "Ready to import" : "Needs attention"}
              </span>
            </div>
            <div className="detected-months">
              {preview.detected_months.map((month) => (
                <span key={month}>
                  <Check size={14} />
                  {monthLabel(month)}
                </span>
              ))}
              {!!preview.net_worth_entries && (
                <span>
                  <Check size={14} />
                  Networth
                </span>
              )}
            </div>
            <div className="preview-counts">
              <div>
                <strong>{preview.expense_entries}</strong>
                <span>expense entries</span>
              </div>
              <div>
                <strong>{preview.income_entries}</strong>
                <span>income entries</span>
              </div>
              <div>
                <strong>{preview.wealth_flow_entries}</strong>
                <span>wealth-flow entries</span>
              </div>
              <div>
                <strong>{preview.net_worth_entries}</strong>
                <span>net-worth balances</span>
              </div>
            </div>
            {!!preview.issues.length && (
              <div className="issue-list">
                <h3>Workbook notes</h3>
                {preview.issues.map((issue, index) => (
                  <div
                    key={`${issue.sheet}-${issue.row}-${index}`}
                    className={issue.severity}
                  >
                    <strong>
                      {issue.sheet}
                      {issue.row ? ` · row ${issue.row}` : ""}
                    </strong>
                    <span>{issue.message}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="replace-row">
              <div>
                <strong>Replace current monthly data</strong>
                <p>
                  This keeps re-imports clean. A net-worth snapshot is added
                  only when its date is newer.
                </p>
              </div>
              <button
                className="primary-button"
                onClick={replaceData}
                disabled={busy || !preview.can_import}
              >
                {busy ? "Importing…" : "Import / Replace Data"}
              </button>
            </div>
          </div>
        )}
      </Card>
    </>
  );
}

export default function FinanceDashboard() {
  const [page, setPage] = useState<PageName>("Overview");
  const [data, setData] = useState<FinanceData>(EMPTY_DATA);
  const [filters, setFilters] = useState<FinanceFilters>(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    let active = true;
    fetchFinanceData(filters)
      .then((response) => {
        if (!active) return;
        setData(response);
        setOffline(false);
      })
      .catch(() => {
        if (active) setOffline(true);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [filters]);
  async function imported() {
    setLoading(true);
    try {
      setData(await fetchFinanceData(filters));
      setOffline(false);
      setPage("Overview");
    } catch {
      setOffline(true);
    } finally {
      setLoading(false);
    }
  }
  let content: ReactNode;
  if (loading && !data.metadata.available_months.length) content = <Loading />;
  else if (page === "Overview")
    content = <OverviewPage data={data} onImport={() => setPage("Import")} />;
  else if (page === "Spending") content = <SpendingPage data={data} />;
  else if (page === "Income") content = <IncomePage data={data} />;
  else if (page === "Net Worth") content = <NetWorthPage data={data} />;
  else if (page === "Compare") content = <ComparePage data={data} />;
  else content = <ImportPage onImported={imported} />;
  return (
    <div className="app-shell">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="brand">
          <MiniLogo />
          <div>
            <strong>Ember</strong>
            <span>Finance analytics</span>
          </div>
          <button
            onClick={() => setMenuOpen(false)}
            aria-label="Close navigation"
          >
            <X size={20} />
          </button>
        </div>
        <nav>
          {NAV_ITEMS.map(([name, Icon]) => (
            <button
              key={name}
              className={page === name ? "active" : ""}
              onClick={() => {
                setPage(name);
                setMenuOpen(false);
              }}
            >
              <Icon size={18} />
              <span>{name}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="privacy">
            <ShieldCheck size={17} />
            <div>
              <strong>Private by design</strong>
              <span>Stored on this Mac</span>
            </div>
          </div>
          {data.metadata.workbook_name && (
            <div className="workbook-source">
              <span>Source workbook</span>
              <strong>{data.metadata.workbook_name}</strong>
            </div>
          )}
        </div>
      </aside>
      <main className="main-content">
        <div className="mobile-top">
          <button
            onClick={() => setMenuOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={21} />
          </button>
          <MiniLogo />
          <strong>Ember</strong>
        </div>
        {page !== "Import" && (
          <FilterBar
            filters={filters}
            setFilters={setFilters}
            months={data.metadata.available_months}
          />
        )}
        {offline && (
          <div className="offline-banner">
            API offline · run <code>./scripts/start-local.sh</code> to use your
            local workbook data.
          </div>
        )}
        <div className="page-content">{content}</div>
      </main>
    </div>
  );
}
