import { useMutation } from '@tanstack/react-query'
import { Download, FileText, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { fintaxApi } from '../lib/api'

export function ReportPage() {
  const report = useMutation({
    mutationFn: fintaxApi.downloadLatestReport,
    onSuccess: (blob) => {
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'fintax-tax-summary.pdf'
      anchor.click()
      URL.revokeObjectURL(url)
    },
  })

  return (
    <section className="filing-page container">
      <p className="eyebrow">YOUR TAX WORKSPACE</p>
      <h1>Reports & filing guidance</h1>
      <p className="filing-page__intro">
        Download your saved engine comparison and review a non-binding filing checklist.
        FinTax AI does not submit returns on your behalf.
      </p>
      <div className="filing-actions">
        <article className="filing-action-card">
          <FileText aria-hidden="true" size={24} />
          <h2>Tax comparison report</h2>
          <p>Includes both saved regimes, saved suggestions, calculation traces, and a disclaimer.</p>
          <button
            className="button button--primary"
            disabled={report.isPending}
            onClick={() => report.mutate()}
            type="button"
          >
            <Download aria-hidden="true" size={16} />
            {report.isPending ? 'Preparing report…' : 'Download PDF'}
          </button>
          {report.isError && <p className="form-error" role="alert">{report.error.message}</p>}
        </article>
        <article className="filing-action-card">
          <ShieldCheck aria-hidden="true" size={24} />
          <h2>Before filing</h2>
          <p>Review likely form candidates and prepare a pre-filled summary for your own use.</p>
          <Link className="button button--primary" to="/filing-guidance">Open filing guidance</Link>
        </article>
      </div>
      <p className="chat-disclaimer">
        Guidance only, not professional tax advice. Verify current eligibility and all amounts
        with the official Income Tax e-Filing portal or a qualified professional.
      </p>
    </section>
  )
}
