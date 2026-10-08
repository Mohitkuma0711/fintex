import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRightLeft, FileQuestion, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import { fintaxApi, type TaxTraceStep } from '../lib/api'
import { formatINRExact } from '../lib/formatters'

const sections = [
  { value: '80C', label: '80C investment or eligible expense' },
  { value: '80D', label: '80D health-insurance premium' },
  { value: '80CCD(1B)', label: '80CCD(1B) NPS contribution' },
  { value: '80E', label: '80E education-loan interest' },
  { value: '24B', label: '24(b) home-loan interest' },
] as const

function ResultCard({
  title,
  regime,
  tax,
}: {
  title: string
  regime: 'old' | 'new'
  tax: string
}) {
  return (
    <article className="simulator-result-card">
      <p className="eyebrow">{title}</p>
      <h3>{regime === 'old' ? 'Old regime' : 'New regime'}</h3>
      <strong>{formatINRExact(tax)}</strong>
      <span>Recommended by the deterministic engine</span>
    </article>
  )
}

function TraceDetails({ title, steps }: { title: string; steps: TaxTraceStep[] }) {
  return (
    <details className="simulator-trace">
      <summary>{title} calculation trace</summary>
      <ol>
        {steps.map((step, index) => (
          <li key={`${step.label}-${index}`}>
            <div><strong>{step.label}</strong><span>{formatINRExact(step.output)}</span></div>
            <p>{step.plain_language_why}</p>
            <code>{step.formula} · {step.rule_reference}</code>
          </li>
        ))}
      </ol>
    </details>
  )
}

export function SimulatorPage() {
  const profileQuery = useQuery({
    queryKey: ['user-profile'],
    queryFn: fintaxApi.getProfile,
  })
  const profile = profileQuery.data?.confirmed_profile ?? null
  const userId = profileQuery.data?.id
  const [kind, setKind] = useState<'deduction' | 'rent'>('deduction')
  const [section, setSection] = useState<(typeof sections)[number]['value']>('80CCD(1B)')
  const [amount, setAmount] = useState('50000')
  const [debouncedAmount, setDebouncedAmount] = useState(amount)

  useEffect(() => {
    const timeout = window.setTimeout(() => setDebouncedAmount(amount), 350)
    return () => window.clearTimeout(timeout)
  }, [amount])

  const validAmount = /^\d+(?:\.\d{1,4})?$/.test(amount)
  const debouncedAmountIsValid = /^\d+(?:\.\d{1,4})?$/.test(debouncedAmount)
  const isDebouncing = amount !== debouncedAmount
  const simulationQuery = useQuery({
    queryKey: [
      'tax-simulation',
      userId,
      profile?.financial_year,
      kind,
      section,
      debouncedAmount,
    ],
    queryFn: () => {
      if (!profile || !debouncedAmountIsValid) throw new Error('Enter a valid non-negative amount.')
      return fintaxApi.simulateTax({
        financial_year: profile.financial_year,
        profile,
        change: kind === 'rent'
          ? { kind, amount: debouncedAmount }
          : { kind, section, amount: debouncedAmount },
      })
    },
    enabled: profile !== null && validAmount && debouncedAmountIsValid && !isDebouncing,
  })

  if (profileQuery.isPending) {
    return (
      <section aria-label="Loading simulator" className="simulator-page container">
        <Skeleton className="dashboard-skeleton dashboard-skeleton--heading" />
        <Skeleton className="simulator-skeleton" />
      </section>
    )
  }

  if (profileQuery.isError) {
    return (
      <section className="simulator-page container">
        <EmptyState
          icon={<FileQuestion aria-hidden="true" size={26} />}
          title="Your profile could not be loaded."
          description={profileQuery.error.message}
          action={<button className="button" onClick={() => void profileQuery.refetch()} type="button">Try again</button>}
        />
      </section>
    )
  }

  if (!profile) {
    return (
      <section className="simulator-page container">
        <EmptyState
          icon={<SlidersHorizontal aria-hidden="true" size={26} />}
          title="Confirm a profile to explore scenarios."
          description="The simulator sends changed inputs to the deterministic tax engine. It does not calculate tax in your browser."
          action={<Link className="button button--primary" to="/review?mode=manual">Enter profile details</Link>}
        />
      </section>
    )
  }

  const result = simulationQuery.data
  const before = result
    ? result.before.recommended_regime === 'old' ? result.before.old_regime : result.before.new_regime
    : null
  const after = result
    ? result.after.recommended_regime === 'old' ? result.after.old_regime : result.after.new_regime
    : null

  return (
    <section className="simulator-page container">
      <header className="simulator-heading">
        <p className="eyebrow">WHAT-IF SIMULATOR · FY {profile.financial_year}</p>
        <h1>Try a scenario. <span>Keep the facts.</span></h1>
        <p>Every result below comes from rerunning both regimes with the verified ruleset.</p>
      </header>

      <section aria-label="Scenario controls" className="simulator-controls">
        <div className="simulator-controls__heading">
          <SlidersHorizontal aria-hidden="true" size={20} />
          <div><h2>Change one input</h2><p>Values update after a short pause while you adjust the control.</p></div>
        </div>
        <label className="simulator-field">
          <span>Scenario type</span>
          <select
            onChange={(event) => {
              const nextKind = event.currentTarget.value as 'deduction' | 'rent'
              setKind(nextKind)
              setAmount(nextKind === 'rent' ? profile.hra_inputs.rent_paid : '50000')
            }}
            value={kind}
          >
            <option value="deduction">Add an eligible deduction / investment</option>
            <option value="rent">Set annual rent paid</option>
          </select>
        </label>
        {kind === 'deduction' && (
          <label className="simulator-field">
            <span>Deduction category</span>
            <select onChange={(event) => setSection(event.currentTarget.value as typeof section)} value={section}>
              {sections.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
        )}
        <div className="simulator-amount">
          <label className="simulator-field" htmlFor="scenario-amount">
            <span>{kind === 'rent' ? 'Annual rent paid (₹)' : 'Additional eligible amount (₹)'}</span>
            <input
              id="scenario-amount"
              inputMode="decimal"
              onChange={(event) => setAmount(event.currentTarget.value)}
              type="text"
              value={amount}
            />
          </label>
          {/^\d+$/.test(amount) && (
            <input
              aria-label="Adjust scenario amount"
              max={kind === 'rent' ? 1200000 : 200000}
              min={0}
              onChange={(event) => setAmount(event.currentTarget.value)}
              step={5000}
              type="range"
              value={Math.min(Number(amount), kind === 'rent' ? 1200000 : 200000)}
            />
          )}
          <p>Scenario inputs are not eligibility advice; the engine applies the selected rules and caps.</p>
        </div>
      </section>

      <section aria-live="polite" aria-label="Scenario results" className="simulator-results">
        {(isDebouncing || simulationQuery.isPending) && <p className="simulator-status" role="status">Recalculating both regimes…</p>}
        {!validAmount && <p className="simulator-error" role="alert">Enter a non-negative amount with up to four decimal places.</p>}
        {simulationQuery.isError && validAmount && (
          <div className="simulator-error" role="alert">
            <p>{simulationQuery.error.message}</p>
            <button className="button" onClick={() => void simulationQuery.refetch()} type="button">Retry</button>
          </div>
        )}
        {result && before && after && !isDebouncing && (
          <>
            <div className="simulator-result-heading">
              <div><p className="eyebrow">ENGINE RESULT · RULES {result.rules_version}</p><h2>Before and after</h2></div>
              <span className="simulator-result-heading__icon"><ArrowRightLeft aria-hidden="true" size={18} /></span>
            </div>
            <div className="simulator-result-grid">
              <ResultCard
                regime={before.regime}
                tax={before.total_tax}
                title={`Before · ${before.financial_year}`}
              />
              <ResultCard
                regime={after.regime}
                tax={after.total_tax}
                title={`After · ${after.financial_year}`}
              />
            </div>
            <div className={`simulator-delta${Number(result.tax_saved) < 0 ? ' simulator-delta--negative' : ''}`}>
              <span>{Number(result.tax_saved) < 0 ? 'Tax increase in this scenario' : 'Tax saved in this scenario'}</span>
              <strong>{formatINRExact(result.tax_saved)}</strong>
              {result.recommended_regime_changed && <p>The recommended regime changed after this input.</p>}
            </div>
            <div className="simulator-traces">
              <TraceDetails steps={result.trace_before} title="Before" />
              <TraceDetails steps={result.trace_after} title="After" />
            </div>
          </>
        )}
      </section>
      <p className="simulator-disclaimer">For planning only. Investment returns, fees, and opportunity cost are not modeled. FinTax AI provides guidance, not professional tax advice.</p>
    </section>
  )
}
