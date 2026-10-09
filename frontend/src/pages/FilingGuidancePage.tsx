import { useQuery } from '@tanstack/react-query'
import { Download, ExternalLink, FileCheck2 } from 'lucide-react'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import { fintaxApi } from '../lib/api'

function exportSummary(summary: Record<string, unknown>) {
  const blob = new Blob([JSON.stringify(summary, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'fintax-prefilled-filing-summary.json'
  anchor.click()
  URL.revokeObjectURL(url)
}

export function FilingGuidancePage() {
  const guidanceQuery = useQuery({
    queryKey: ['filing-guidance'],
    queryFn: fintaxApi.getFilingGuidance,
  })
  if (guidanceQuery.isPending) {
    return (
      <section className="filing-page container" aria-label="Loading filing guidance">
        <Skeleton className="dashboard-skeleton dashboard-skeleton--heading" />
        <Skeleton className="dashboard-skeleton dashboard-skeleton--card" />
      </section>
    )
  }
  if (guidanceQuery.isError) {
    return (
      <section className="filing-page container">
        <EmptyState
          icon={<FileCheck2 aria-hidden="true" size={26} />}
          title="Filing guidance is unavailable."
          description={guidanceQuery.error.message}
          action={
            <button className="button" onClick={() => void guidanceQuery.refetch()} type="button">
              Try again
            </button>
          }
        />
      </section>
    )
  }
  const guidance = guidanceQuery.data
  return (
    <section className="filing-page container">
      <p className="eyebrow">FILING PREPARATION · GUIDANCE ONLY</p>
      <h1>Prepare to file with confidence.</h1>
      <p className="filing-page__intro">{guidance.guidance}</p>
      {guidance.likely_forms.length > 0 && (
        <section className="filing-card" aria-labelledby="candidate-forms">
          <h2 id="candidate-forms">Forms to review</h2>
          <ul className="filing-form-list">
            {guidance.likely_forms.map((form) => <li key={form}>{form}</li>)}
          </ul>
        </section>
      )}
      <div className="filing-checklist-grid">
        <section className="filing-card">
          <h2>Schedules to review</h2>
          {guidance.schedules_to_review.length
            ? <ul>{guidance.schedules_to_review.map((item) => <li key={item}>{item}</li>)}</ul>
            : <p>Confirm your profile to see a checklist.</p>}
        </section>
        <section className="filing-card">
          <h2>Documents to prepare</h2>
          {guidance.documents_to_prepare.length
            ? <ul>{guidance.documents_to_prepare.map((item) => <li key={item}>{item}</li>)}</ul>
            : <p>Confirm your profile to see a checklist.</p>}
        </section>
      </div>
      {guidance.prefilled_summary && (
        <button
          className="button button--primary"
          onClick={() => exportSummary(guidance.prefilled_summary!)}
          type="button"
        >
          <Download aria-hidden="true" size={16} /> Export pre-filled summary
        </button>
      )}
      <a className="filing-source-link" href={guidance.official_source} rel="noreferrer" target="_blank">
        Verify on the official e-Filing portal <ExternalLink aria-hidden="true" size={14} />
      </a>
      <p className="chat-disclaimer">{guidance.disclaimer} We do not submit returns on your behalf.</p>
    </section>
  )
}
