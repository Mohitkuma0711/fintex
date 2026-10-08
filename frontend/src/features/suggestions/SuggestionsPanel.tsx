import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowUpRight, BadgeCheck, CircleHelp, ShieldAlert } from 'lucide-react'
import { Link } from 'react-router-dom'
import { ApiError, fintaxApi, type ConfirmedTaxpayerProfile } from '../../lib/api'
import { formatINRExact } from '../../lib/formatters'
import { Skeleton } from '../../components/ui/Skeleton'

function SuggestionCard({
  suggestion,
  onPlanChange,
  isSaving,
  maximumBenefit,
}: {
  suggestion: Awaited<ReturnType<typeof fintaxApi.getSuggestions>>['suggestions'][number]
  onPlanChange: (id: string, planned: boolean) => void
  isSaving: boolean
  maximumBenefit: number
}) {
  const benefit = Number(suggestion.net_benefit)
  const impactWidth = Number.isFinite(benefit) && benefit > 0
    ? `${Math.min(100, Math.max(8, benefit / Math.max(maximumBenefit, 1) * 100))}%`
    : '0%'

  return (
    <article className="suggestion-card">
      <div className="suggestion-card__top">
        <div>
          <p className="eyebrow">{suggestion.eligible_regime ? `${suggestion.eligible_regime} regime` : 'Profile check'}</p>
          <h3>{suggestion.title}</h3>
          <p className="suggestion-card__product">{suggestion.product}</p>
        </div>
        <div className="suggestion-card__impact">
          <span>Tax saved</span>
          <strong>{formatINRExact(suggestion.tax_saved)}</strong>
        </div>
      </div>
      <div aria-label={`Tax impact ${impactWidth}`} className="suggestion-impact-track">
        <span style={{ width: impactWidth }} />
      </div>
      <dl className="suggestion-card__facts">
        <div><dt>Eligible amount</dt><dd>{formatINRExact(suggestion.amount_to_invest)}</dd></div>
        <div><dt>Lock-in</dt><dd>{suggestion.lock_in_period || 'No verified lock-in data'}</dd></div>
      </dl>
      <p className="suggestion-card__liquidity">{suggestion.liquidity_note}</p>
      <details className="suggestion-why">
        <summary><CircleHelp aria-hidden="true" size={16} /> Why this applies</summary>
        <p>{suggestion.explanation}</p>
        <p><strong>Rule reference:</strong> <code>{suggestion.rule_reference}</code></p>
        <p><strong>Net benefit:</strong> tax saved only. Investment returns, fees, and opportunity cost are not estimated.</p>
      </details>
      <div className="suggestion-card__actions">
        <label>
          <input
            checked={suggestion.planned_to_do}
            disabled={isSaving}
            onChange={(event) => onPlanChange(suggestion.id, event.currentTarget.checked)}
            type="checkbox"
          />
          <span>Plan to do</span>
        </label>
        {suggestion.alternative_group && <span className="suggestion-alternative">Alternative within {suggestion.alternative_group}</span>}
      </div>
    </article>
  )
}

export function SuggestionsPanel({
  profile,
  userId,
}: {
  profile: ConfirmedTaxpayerProfile
  userId: string
}) {
  const queryClient = useQueryClient()
  const suggestionsQuery = useQuery({
    queryKey: ['tax-suggestions', userId, profile.financial_year],
    queryFn: () => fintaxApi.getSuggestions(profile),
  })
  const planMutation = useMutation({
    mutationFn: ({ id, planned }: { id: string; planned: boolean }) =>
      fintaxApi.setSuggestionPlanned(id, planned),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tax-suggestions', userId] }),
  })

  if (suggestionsQuery.isPending) {
    return (
      <section aria-label="Loading tax-saving suggestions" className="suggestions-section">
        <header className="suggestions-heading">
          <div><p className="eyebrow">SUGGEST</p><h2>Personalized next steps</h2></div>
        </header>
        <div className="suggestion-list">
          <Skeleton className="suggestion-skeleton" />
          <Skeleton className="suggestion-skeleton" />
        </div>
      </section>
    )
  }

  if (suggestionsQuery.isError) {
    const termsUnavailable = suggestionsQuery.error instanceof ApiError &&
      suggestionsQuery.error.status === 503
    return (
      <section aria-labelledby="suggestions-heading" className="suggestions-section">
        <header className="suggestions-heading">
          <div><p className="eyebrow">SUGGEST</p><h2 id="suggestions-heading">Personalized next steps</h2></div>
        </header>
        <div className="suggestions-notice" role="alert">
          <ShieldAlert aria-hidden="true" size={21} />
          <div>
            <h3>{termsUnavailable ? 'Suggestions are waiting on verified rule terms' : 'Suggestions could not be loaded'}</h3>
            <p>{termsUnavailable
              ? 'No product recommendations are shown until relevant lock-in and liquidity terms are verified against official sources. Your tax results remain separate.'
              : suggestionsQuery.error.message}</p>
            {!termsUnavailable && <button className="button" onClick={() => void suggestionsQuery.refetch()} type="button">Try again</button>}
          </div>
        </div>
      </section>
    )
  }

  const data = suggestionsQuery.data
  const maximumBenefit = Math.max(
    0,
    ...data.suggestions.map((suggestion) => Number(suggestion.net_benefit)),
  )
  return (
    <section aria-labelledby="suggestions-heading" className="suggestions-section">
      <header className="suggestions-heading">
        <div>
          <p className="eyebrow">SUGGEST · FY {data.financial_year}</p>
          <h2 id="suggestions-heading">Personalized next steps</h2>
          <p>Engine-tested opportunities, ranked by tax saved. Rules {data.rules_version}.</p>
        </div>
        <Link className="button" to="/simulator">Explore a scenario <ArrowUpRight aria-hidden="true" size={16} /></Link>
      </header>
      <div className="savings-potential">
        <BadgeCheck aria-hidden="true" size={20} />
        <div><span>Potential tax savings</span><strong>{formatINRExact(data.savings_potential)}</strong></div>
        <p>{data.planned_count} planned · alternatives counted once · no return assumptions.</p>
      </div>
      {planMutation.isError && (
        <p className="suggestion-mutation-error" role="alert">
          Could not update your plan: {planMutation.error.message}. Please try again.
        </p>
      )}
      {data.suggestions.length === 0 ? (
        <p className="suggestions-empty">No additional tax-saving opportunity was identified from your confirmed profile and eligible rules.</p>
      ) : (
        <div className="suggestion-list">
          {data.suggestions.map((suggestion) => (
            <SuggestionCard
              isSaving={planMutation.isPending}
              key={suggestion.id}
              maximumBenefit={maximumBenefit}
              onPlanChange={(id, planned) => planMutation.mutate({ id, planned })}
              suggestion={suggestion}
            />
          ))}
        </div>
      )}
      <p className="suggestions-disclaimer">Plan tracking does not execute investments or change your profile. Confirm eligibility with original documents; this is guidance, not professional tax advice.</p>
    </section>
  )
}
