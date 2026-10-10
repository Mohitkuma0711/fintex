import { useQuery } from '@tanstack/react-query'
import { ArrowRight, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import { SuggestionsPanel } from '../features/suggestions/SuggestionsPanel'
import { fintaxApi } from '../lib/api'

export function TaxAdvisorPage() {
  const profileQuery = useQuery({ queryKey: ['user-profile'], queryFn: fintaxApi.getProfile })
  const profile = profileQuery.data?.confirmed_profile ?? null

  if (profileQuery.isPending) {
    return <section className="container"><Skeleton className="dashboard-skeleton dashboard-skeleton--heading" /></section>
  }
  if (profileQuery.isError) {
    return <section className="container"><EmptyState icon={<ShieldCheck size={26} />} title="Advisor unavailable" description={profileQuery.error.message} action={<button className="button" onClick={() => void profileQuery.refetch()} type="button">Try again</button>} /></section>
  }
  if (!profile) {
    return (
      <section className="container">
        <EmptyState
          icon={<ShieldCheck size={26} />}
          title="Confirm your profile first"
          description="The advisor only uses confirmed facts and verified rules. Upload a document or enter your details manually before requesting recommendations."
          action={<Link className="button button--primary" to="/upload">Upload a document <ArrowRight size={16} /></Link>}
        />
      </section>
    )
  }

  return (
    <section className="container">
      <header className="dashboard-heading">
        <p className="eyebrow">AI TAX-SAVING ADVISOR · FY {profile.financial_year}</p>
        <h1>Lawful options, <span>with evidence.</span></h1>
        <p>Recommendations come from the verified rules engine. Gemini may explain a verified result, but cannot invent a deduction or calculate your tax.</p>
      </header>
      <SuggestionsPanel profile={profile} userId={profileQuery.data?.id ?? 'current-user'} />
      <p className="suggestions-disclaimer">Potential savings are estimates, not guarantees. Confirm eligibility and evidence with the official source or a qualified tax professional.</p>
    </section>
  )
}
