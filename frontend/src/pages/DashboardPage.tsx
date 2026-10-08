import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, CircleHelp, ShieldCheck, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { CountUp } from '../components/motion/CountUp'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import { ApiError, fintaxApi, type TaxResult, type TaxTraceStep } from '../lib/api'
import { formatINR } from '../lib/formatters'
import { SuggestionsPanel } from '../features/suggestions/SuggestionsPanel'

const DashboardCharts = lazy(async () => {
  const module = await import('../features/dashboard/DashboardCharts')
  return { default: module.DashboardCharts }
})

function amount(value: string): number {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function TaxSummaryCard({
  result,
  recommended,
  onExplain,
}: {
  result: TaxResult
  recommended: boolean
  onExplain: (step: TaxTraceStep) => void
}) {
  const totalTaxStep = result.trace.find((step) => step.label === 'Total tax')
  const taxableIncomeStep = result.trace.find((step) => step.label === 'Taxable income')

  return (
    <article className={`dashboard-regime-card${recommended ? ' dashboard-regime-card--recommended' : ''}`}>
      <div className="dashboard-regime-card__top">
        <div>
          <p className="eyebrow">{result.regime === 'old' ? 'OLD REGIME' : 'NEW REGIME'}</p>
          <h2>{result.regime === 'old' ? 'Old tax regime' : 'New tax regime'}</h2>
        </div>
        {recommended && <span className="dashboard-recommended"><ShieldCheck size={15} /> Recommended</span>}
      </div>
      <button
        aria-label={`Why is total tax ${formatINR(amount(result.total_tax))}?`}
        className="dashboard-tax-total"
        disabled={!totalTaxStep}
        onClick={() => totalTaxStep && onExplain(totalTaxStep)}
        type="button"
      >
        <span>Total tax</span>
        <strong><CountUp value={amount(result.total_tax)} /></strong>
        <small><CircleHelp aria-hidden="true" size={14} /> Why this amount?</small>
      </button>
      <button
        className="dashboard-tax-detail"
        disabled={!taxableIncomeStep}
        onClick={() => taxableIncomeStep && onExplain(taxableIncomeStep)}
        type="button"
      >
        <span>Taxable income</span><strong>{formatINR(amount(result.taxable_income))}</strong>
      </button>
      <p className="dashboard-regime-card__foot">
        {result.act} · Rules {result.rules_version}
      </p>
    </article>
  )
}

function WhyPanel({
  step,
  onClose,
}: {
  step: TaxTraceStep
  onClose: () => void
}) {
  const panelRef = useRef<HTMLElement>(null)
  useEffect(() => {
    panelRef.current?.focus()
  }, [])

  return (
    <aside
      aria-labelledby="why-heading"
      aria-modal="false"
      className="dashboard-why-panel"
      ref={panelRef}
      role="dialog"
      tabIndex={-1}
    >
      <div className="dashboard-why-panel__top">
        <div>
          <p className="eyebrow">CALCULATION TRACE</p>
          <h2 id="why-heading">{step.label}</h2>
        </div>
        <button aria-label="Close calculation explanation" className="dashboard-icon-button" onClick={onClose} type="button">
          <X aria-hidden="true" size={18} />
        </button>
      </div>
      <p className="dashboard-why-panel__plain">{step.plain_language_why}</p>
      <dl className="dashboard-trace-details">
        <div><dt>Formula</dt><dd><code>{step.formula}</code></dd></div>
        <div><dt>Inputs</dt><dd>
          {Object.entries(step.inputs).map(([label, value]) => (
            <span className="dashboard-trace-input" key={label}>
              <span>{label.replaceAll('_', ' ')}</span><strong>{value ?? 'Not applicable'}</strong>
            </span>
          ))}
        </dd></div>
        <div><dt>Calculated output</dt><dd className="dashboard-trace-output">{formatINR(amount(step.output))}</dd></div>
        <div><dt>Rule reference</dt><dd><code>{step.rule_reference}</code></dd></div>
      </dl>
    </aside>
  )
}

export function DashboardPage() {
  const [activeTrace, setActiveTrace] = useState<TaxTraceStep | null>(null)
  const traceTrigger = useRef<HTMLElement | null>(null)
  const openTrace = (step: TaxTraceStep) => {
    const activeElement = document.activeElement
    if (activeElement instanceof HTMLElement) traceTrigger.current = activeElement
    setActiveTrace(step)
  }
  const closeTrace = () => {
    setActiveTrace(null)
    requestAnimationFrame(() => traceTrigger.current?.focus())
  }
  const profileQuery = useQuery({
    queryKey: ['user-profile'],
    queryFn: fintaxApi.getProfile,
  })
  const profile = profileQuery.data?.confirmed_profile ?? null
  const comparisonQuery = useQuery({
    queryKey: ['tax-comparison', profileQuery.data?.id, profile?.financial_year],
    queryFn: () => {
      if (!profile) throw new Error('A confirmed profile is required before calculating tax.')
      return fintaxApi.compareTax({
        financial_year: profile.financial_year,
        profile,
      })
    },
    enabled: profile !== null,
  })

  if (profileQuery.isPending) {
    return (
      <section aria-label="Loading tax dashboard" className="dashboard-page container">
        <Skeleton className="dashboard-skeleton dashboard-skeleton--heading" />
        <div className="dashboard-regime-grid">
          <Skeleton className="dashboard-skeleton dashboard-skeleton--card" />
          <Skeleton className="dashboard-skeleton dashboard-skeleton--card" />
        </div>
        <Skeleton className="dashboard-skeleton dashboard-skeleton--chart" />
      </section>
    )
  }

  if (profileQuery.isError) {
    return (
      <section className="dashboard-page container">
        <EmptyState
          icon={<ShieldCheck aria-hidden="true" size={26} />}
          title="Your workspace could not be loaded."
          description={profileQuery.error.message}
          action={<button className="button button--primary" onClick={() => void profileQuery.refetch()} type="button">Try again</button>}
        />
      </section>
    )
  }

  if (!profile) {
    return (
      <section className="dashboard-page container">
        <EmptyState
          icon={<ShieldCheck aria-hidden="true" size={26} />}
          title="Start with your verified tax profile."
          description="Confirm your income details first. We’ll use that profile to request an auditable comparison from the deterministic tax rules engine."
          action={(
            <div className="dashboard-empty-actions">
              <Link className="button button--primary" to="/review?mode=manual">Enter details manually <ArrowRight size={16} /></Link>
              <Link className="button" to="/upload">Upload a document</Link>
            </div>
          )}
        />
      </section>
    )
  }

  if (comparisonQuery.isPending) {
    return (
      <section aria-label="Calculating tax comparison" className="dashboard-page container">
        <Skeleton className="dashboard-skeleton dashboard-skeleton--heading" />
        <p className="dashboard-calculating" role="status">Preparing the comparison using verified rules for FY {profile.financial_year}…</p>
        <div className="dashboard-regime-grid">
          <Skeleton className="dashboard-skeleton dashboard-skeleton--card" />
          <Skeleton className="dashboard-skeleton dashboard-skeleton--card" />
        </div>
      </section>
    )
  }

  if (comparisonQuery.isError) {
    const rulesUnavailable = comparisonQuery.error instanceof ApiError && comparisonQuery.error.status === 503
    return (
      <section className="dashboard-page container">
        <header className="dashboard-heading">
          <p className="eyebrow">YOUR TAX WORKSPACE · FY {profile.financial_year}</p>
          <h1>Your profile is ready. <span>The calculation isn’t.</span></h1>
        </header>
        <div className="dashboard-rules-notice" role="alert">
          <ShieldCheck aria-hidden="true" size={22} />
          <div>
            <h2>{rulesUnavailable ? 'Verified tax rules are not configured yet' : 'We could not calculate this comparison'}</h2>
            <p>
              {rulesUnavailable
                ? 'FinTax AI will not estimate or invent tax rates. This calculation becomes available when the relevant official rules are verified and versioned.'
                : comparisonQuery.error.message}
            </p>
            {!rulesUnavailable && (
              <button className="button" onClick={() => void comparisonQuery.refetch()} type="button">Retry calculation</button>
            )}
          </div>
        </div>
        <p className="dashboard-disclaimer">Guidance only, not professional tax advice. Your confirmed profile remains private to your account.</p>
      </section>
    )
  }

  const comparison = comparisonQuery.data.result
  const recommendedResult = comparison.recommended_regime === 'old'
    ? comparison.old_regime
    : comparison.new_regime

  return (
    <section className="dashboard-page container">
      <header className="dashboard-heading">
        <div>
          <p className="eyebrow">YOUR TAX WORKSPACE · FY {profile.financial_year}</p>
          <h1>A clearer view of <span>your tax.</span></h1>
          <p>Two regimes, one deterministic calculation, and a trace behind every amount.</p>
        </div>
        <Link className="button dashboard-edit-link" to="/review?mode=manual">Update profile</Link>
      </header>

      <section aria-label="Regime recommendation" className="dashboard-regime-grid">
        <TaxSummaryCard
          onExplain={openTrace}
          recommended={comparison.recommended_regime === 'old'}
          result={comparison.old_regime}
        />
        <TaxSummaryCard
          onExplain={openTrace}
          recommended={comparison.recommended_regime === 'new'}
          result={comparison.new_regime}
        />
      </section>

      <section aria-live="polite" className="dashboard-savings">
        <span className="dashboard-savings__sparkle" aria-hidden="true">✦</span>
        <div>
          <p className="eyebrow">RECOMMENDED · {recommendedResult.regime === 'old' ? 'OLD' : 'NEW'} REGIME</p>
          <h2>You save <strong><CountUp value={amount(comparison.saving)} /></strong></h2>
          <p>Compared with the other regime for the same confirmed profile.</p>
        </div>
        {recommendedResult.trace.find((step) => step.label === 'Total tax') && (
          <button
            aria-label="Why is this regime recommended?"
            className="dashboard-savings__why"
            onClick={() => {
              const totalTaxStep = recommendedResult.trace.find((step) => step.label === 'Total tax')
              if (totalTaxStep) openTrace(totalTaxStep)
            }}
            type="button"
          >
            <CircleHelp aria-hidden="true" size={18} /> How was this decided?
          </button>
        )}
      </section>

      <Suspense fallback={<div aria-label="Loading charts" className="dashboard-regime-grid"><Skeleton className="dashboard-skeleton dashboard-skeleton--chart" /><Skeleton className="dashboard-skeleton dashboard-skeleton--chart" /></div>}>
        <DashboardCharts
          newRegime={comparison.new_regime}
          oldRegime={comparison.old_regime}
          onExplain={openTrace}
          profile={profile}
        />
      </Suspense>

      <SuggestionsPanel profile={profile} userId={profileQuery.data.id} />
      {activeTrace && <WhyPanel onClose={closeTrace} step={activeTrace} />}
      <p className="dashboard-disclaimer">FinTax AI provides guidance, not professional tax advice. Review your source documents and consult a qualified professional when needed.</p>
    </section>
  )
}
