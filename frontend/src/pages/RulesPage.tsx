import { useQuery } from '@tanstack/react-query'
import { ExternalLink, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { fintaxApi } from '../lib/api'

const money = (value: string | null) => value ? `₹${Number(value).toLocaleString('en-IN')}` : 'Not specified'

export function RulesPage() {
  const rules = useQuery({ queryKey: ['tax-rules-summary'], queryFn: fintaxApi.getRulesSummary })

  if (rules.isLoading) return <main className="page-shell"><p>Loading verified tax rules…</p></main>
  if (rules.isError || !rules.data) {
    return <main className="page-shell"><h1>Verified rules unavailable</h1><p>Calculations remain blocked until the ruleset is available.</p></main>
  }

  const data = rules.data
  return (
    <main className="page-shell">
      <Link to="/dashboard">← Back to workspace</Link>
      <p className="eyebrow">RULES TRANSPARENCY</p>
      <h1>Tax rules used by FinTax AI</h1>
      <p>
        {data.financial_year} (AY {data.assessment_year}) · {data.governing_act} · verified {data.verified_on}
      </p>
      <div className="card-grid">
        {Object.entries(data.regimes).map(([name, regime]) => (
          <section className="card" key={name}>
            <h2>{name === 'old' ? 'Old regime' : 'New regime'}</h2>
            <p>Standard deduction: <strong>{money(regime.standard_deduction)}</strong></p>
            <p>87A rebate maximum: <strong>{money(regime.rebate)}</strong></p>
            <p>Health and education cess: <strong>{regime.cess_rate ?? 'Not specified'}</strong></p>
            <h3>Tax slabs</h3>
            <ul>
              {regime.slabs.map((slab, index) => (
                <li key={`${name}-slab-${index}`}>
                  {money(slab.lower)} to {slab.upper ? money(slab.upper) : 'above'} at {slab.rate}
                </li>
              ))}
            </ul>
            <h3>Deduction heads</h3>
            <ul>
              {Object.entries(regime.deductions).map(([key, deduction]) => (
                <li key={key}>{key}: {deduction.enabled ? `up to ${money(deduction.limit)}` : 'not enabled'}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <section className="card">
        <h2>Verified tax-saving opportunities</h2>
        <p>These are suggestion paths the engine can calculate. Gemini cannot create new tax rules.</p>
        <ul>
          {data.verified_suggestions.map((suggestion) => (
            <li key={suggestion.key}>
              <strong>{suggestion.title}</strong> ({suggestion.section_ref ?? suggestion.key})
              {' '}<a href={suggestion.source_url} target="_blank" rel="noreferrer">Official source <ExternalLink aria-hidden="true" size={13} /></a>
            </li>
          ))}
        </ul>
      </section>
      <section className="card">
        <h2><ShieldCheck aria-hidden="true" size={20} /> Deliberately blocked until verified</h2>
        <ul>{data.blocked_until_verified.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
    </main>
  )
}
