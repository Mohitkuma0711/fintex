import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { ConfirmedTaxpayerProfile, TaxResult, TaxTraceStep } from '../../lib/api'
import { formatINR } from '../../lib/formatters'

interface DashboardChartsProps {
  profile: ConfirmedTaxpayerProfile
  oldRegime: TaxResult
  newRegime: TaxResult
  onExplain: (step: TaxTraceStep) => void
}

const chartColors = ['var(--brand)', 'var(--green-600)', 'var(--amber-600)', '#8d70d6', '#27a7b5']

function CurrencyTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: readonly { name?: unknown; value?: unknown }[]
  label?: string | number
}) {
  if (!active || !payload?.length) return null
  const entries = payload.filter(
    (entry): entry is { name: string; value: number } =>
      typeof entry.name === 'string' &&
      typeof entry.value === 'number' &&
      Number.isFinite(entry.value),
  )
  if (!entries.length) return null
  return (
    <div className="dashboard-chart-tooltip">
      {label !== undefined && <strong>{label}</strong>}
      {entries.map((entry) => (
        <p key={entry.name}><span>{entry.name}</span><b>{formatINR(entry.value)}</b></p>
      ))}
    </div>
  )
}

function amount(value: string): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function findTrace(result: TaxResult, label: string): TaxTraceStep | undefined {
  return result.trace.find((step) => step.label === label)
}

export function DashboardCharts({
  profile,
  oldRegime,
  newRegime,
  onExplain,
}: DashboardChartsProps) {
  const salaryData = [
    ['Basic salary', profile.salary_components.basic_salary],
    ['Dearness allowance', profile.salary_components.dearness_allowance],
    ['HRA', profile.salary_components.hra_received],
    ['Other allowances', profile.salary_components.other_allowances],
    ['Other income', profile.other_income],
  ]
    .map(([name, value]) => ({ name, value: amount(value as string) }))
    .filter((item) => item.value > 0)

  const comparisonData = [
    { name: 'Old regime', tax: amount(oldRegime.total_tax) },
    { name: 'New regime', tax: amount(newRegime.total_tax) },
  ]
  const slabSteps = (oldRegime.regime === 'old' ? oldRegime : newRegime).trace.filter(
    (step) => step.label.startsWith('Tax slab '),
  )
  const slabData = slabSteps.reduce<{
    data: { name: string; base: number; tax: number }[]
    total: number
  }>(
    (accumulator, step) => {
      const slabTax = amount(step.output)
      return {
        data: [
          ...accumulator.data,
          {
            name: step.label.replace('Tax slab ', 'Slab '),
            base: accumulator.total,
            tax: slabTax,
          },
        ],
        total: accumulator.total + slabTax,
      }
    },
    { data: [], total: 0 },
  ).data
  const grossIncomeStep = findTrace(oldRegime, 'Gross income')

  return (
    <div className="dashboard-charts">
      <section aria-labelledby="salary-chart-title" className="dashboard-chart-card">
        <div className="dashboard-chart-card__heading">
          <div>
            <p className="eyebrow">INCOME PROFILE</p>
            <h2 id="salary-chart-title">Where income comes from</h2>
          </div>
          {grossIncomeStep && (
            <button
              className="dashboard-why-link"
              onClick={() => onExplain(grossIncomeStep)}
              type="button"
            >
              Why this total?
            </button>
          )}
        </div>
        {salaryData.length ? (
          <div aria-label="Income composition" className="dashboard-chart" role="img">
            <ResponsiveContainer height={244} width="100%">
              <PieChart>
                <Pie
                  data={salaryData}
                  dataKey="value"
                  innerRadius={66}
                  nameKey="name"
                  outerRadius={98}
                  paddingAngle={3}
                >
                  {salaryData.map((item, index) => (
                    <Cell fill={chartColors[index % chartColors.length]} key={item.name} />
                  ))}
                </Pie>
                <Tooltip content={(props) => <CurrencyTooltip {...props} />} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="dashboard-chart-empty">No income components were supplied in the confirmed profile.</p>
        )}
        <div className="dashboard-chart-values">
          {salaryData.map((item) => (
            <button
              key={item.name}
              onClick={() => grossIncomeStep && onExplain(grossIncomeStep)}
              type="button"
            >
              <span>{item.name}</span><strong>{formatINR(item.value)}</strong>
            </button>
          ))}
        </div>
      </section>

      <section aria-labelledby="regime-chart-title" className="dashboard-chart-card">
        <div className="dashboard-chart-card__heading">
          <div>
            <p className="eyebrow">REGIME COMPARISON</p>
            <h2 id="regime-chart-title">Tax by regime</h2>
          </div>
          <span className="dashboard-chart-caption">Calculated by the tax rules engine</span>
        </div>
        <div aria-label="Tax comparison by regime" className="dashboard-chart" role="img">
          <ResponsiveContainer height={244} width="100%">
            <BarChart data={comparisonData} margin={{ top: 10, right: 16, bottom: 4, left: 0 }}>
              <CartesianGrid stroke="var(--line)" strokeDasharray="3 5" vertical={false} />
              <XAxis axisLine={false} dataKey="name" tickLine={false} />
              <YAxis axisLine={false} tickFormatter={(value: number) => formatINR(value)} tickLine={false} />
              <Tooltip content={(props) => <CurrencyTooltip {...props} />} />
              <Bar dataKey="tax" radius={[8, 8, 0, 0]}>
                {comparisonData.map((item, index) => (
                  <Cell
                    fill={index === 0 ? 'var(--brand)' : 'var(--green-600)'}
                    key={item.name}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="dashboard-chart-values">
          {[oldRegime, newRegime].map((result) => {
            const step = findTrace(result, 'Total tax')
            return (
              <button key={result.regime} onClick={() => step && onExplain(step)} type="button">
                <span>{result.regime === 'old' ? 'Old regime' : 'New regime'}</span>
                <strong>{formatINR(amount(result.total_tax))}</strong>
              </button>
            )
          })}
        </div>
      </section>

      <section aria-labelledby="slab-chart-title" className="dashboard-chart-card dashboard-chart-card--wide">
        <div className="dashboard-chart-card__heading">
          <div>
            <p className="eyebrow">TAX BREAKDOWN</p>
            <h2 id="slab-chart-title">Tax applied by slab</h2>
          </div>
          <span className="dashboard-chart-caption">
            {oldRegime.regime === 'old' ? 'Old regime' : 'New regime'} · before rebate and cess
          </span>
        </div>
        {slabData.length ? (
          <div aria-label="Tax by slab waterfall" className="dashboard-chart" role="img">
            <ResponsiveContainer height={250} width="100%">
              <BarChart data={slabData} margin={{ top: 10, right: 20, bottom: 4, left: 0 }}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="3 5" vertical={false} />
                <XAxis axisLine={false} dataKey="name" tickLine={false} />
                <YAxis axisLine={false} tickFormatter={(value: number) => formatINR(value)} tickLine={false} />
                <Tooltip content={(props) => <CurrencyTooltip {...props} />} />
                <Bar dataKey="base" fill="transparent" stackId="waterfall" />
                <Bar dataKey="tax" fill="var(--brand)" radius={[6, 6, 0, 0]} stackId="waterfall" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="dashboard-chart-empty">There are no tax-slab steps in this calculation.</p>
        )}
        <div className="dashboard-chart-values">
          {slabSteps.map((step) => (
            <button key={step.label} onClick={() => onExplain(step)} type="button">
              <span>{step.label}</span><strong>{formatINR(amount(step.output))}</strong>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
