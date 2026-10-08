import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { useForm, useWatch, type FieldPath } from 'react-hook-form'
import { z } from 'zod'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  CircleCheck,
  FileText,
  ShieldCheck,
} from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import {
  fintaxApi,
  type ConfirmedTaxpayerProfile,
  type ExtractedField,
} from '../lib/api'

const money = z.string().trim().regex(/^\d+(?:\.\d{1,4})?$/, 'Enter a non-negative amount with up to four decimal places.')

const reviewSchema = z.object({
  employment_type: z.enum(['employee', 'business_freelancer']),
  field_values: z.record(z.string(), z.string()),
  salary_components: z.object({
    basic_salary: money,
    dearness_allowance: money,
    hra_received: money,
    other_allowances: money,
  }),
  hra_inputs: z.object({ rent_paid: money }),
  other_income: money,
  deductions_claimed: z.object({
    section_80c: money,
    section_80d: money,
    section_80ccd_1b: money,
    section_80e: money,
    section_24b: money,
  }),
  age_bracket: z.enum(['below_60', '60_to_79', '80_plus']),
  city_type: z.enum(['metro', 'non_metro']),
  financial_year: z.string().regex(/^\d{4}-\d{2}$/, 'Choose a financial year.'),
  planning_eligibility: z.object({
    health_insurance_eligible: z.boolean(),
    eligible_health_insurance_premium: money,
    education_loan_eligible: z.boolean(),
    eligible_education_loan_interest: money,
    home_loan_eligible: z.boolean(),
    eligible_home_loan_interest: money,
  }),
  consent_given: z.boolean(),
}).superRefine((values, context) => {
  if (!values.consent_given) {
    context.addIssue({
      code: 'custom',
      path: ['consent_given'],
      message: 'Please provide consent before continuing.',
    })
  }
})

type ReviewFormValues = z.infer<typeof reviewSchema>

function isExtractedField(value: unknown): value is ExtractedField {
  return typeof value === 'object' && value !== null &&
    'value' in value && (typeof value.value === 'string' || value.value === null) &&
    'confidence' in value && typeof value.confidence === 'number' &&
    'source_page' in value &&
    (typeof value.source_page === 'number' || value.source_page === null)
}

function visibleFields(fields: Record<string, unknown>): [string, ExtractedField][] {
  const entries = Object.entries(fields).filter(
    (entry): entry is [string, ExtractedField] => isExtractedField(entry[1]),
  )
  const deductions = fields.deduction_items
  if (Array.isArray(deductions)) {
    deductions.forEach((item, index) => {
      if (typeof item !== 'object' || item === null || !('section' in item) ||
          typeof item.section !== 'string' || !('amount' in item) || !isExtractedField(item.amount)) {
        return
      }
      const amountField = item.amount
      entries.push([
        `deduction_items.${index}.section`,
        {
          value: item.section,
          confidence: amountField.confidence,
          source_page: amountField.source_page,
        },
      ])
      entries.push([`deduction_items.${index}.amount`, amountField])
    })
  }
  return entries
}

function formatLabel(key: string) {
  return key.replaceAll('_', ' ').replaceAll('.', ' · ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function emptyForm(): ReviewFormValues {
  const now = new Date()
  const startYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1
  return {
    employment_type: 'employee',
    field_values: {},
    salary_components: {
      basic_salary: '0',
      dearness_allowance: '0',
      hra_received: '0',
      other_allowances: '0',
    },
    hra_inputs: { rent_paid: '0' },
    other_income: '0',
    deductions_claimed: {
      section_80c: '0',
      section_80d: '0',
      section_80ccd_1b: '0',
      section_80e: '0',
      section_24b: '0',
    },
    age_bracket: 'below_60',
    city_type: 'non_metro',
    financial_year: `${startYear}-${String(startYear + 1).slice(-2)}`,
    planning_eligibility: {
      health_insurance_eligible: false,
      eligible_health_insurance_premium: '0',
      education_loan_eligible: false,
      eligible_education_loan_interest: '0',
      home_loan_eligible: false,
      eligible_home_loan_interest: '0',
    },
    consent_given: false,
  }
}

function buildProfile(values: ReviewFormValues): ConfirmedTaxpayerProfile {
  return {
    employment_type: values.employment_type,
    consent_given: true,
    salary_components: values.salary_components,
    hra_inputs: values.hra_inputs,
    other_income: values.other_income,
    deductions_claimed: values.deductions_claimed,
    age_bracket: values.age_bracket,
    city_type: values.city_type,
    financial_year: values.financial_year,
    planning_eligibility: values.planning_eligibility,
  }
}

function WorkflowStepper({ manualMode }: { manualMode: boolean }) {
  const steps = ['Upload', 'Extract', 'Verify', 'Calculate', 'Suggest', 'Explain & Act']
  return (
    <ol aria-label="Tax workflow progress" className="verify-stepper">
      {steps.map((step, index) => {
        const state = index < 2
          ? manualMode ? 'skipped' : 'complete'
          : index === 2 ? 'active' : 'waiting'
        return (
          <motion.li
            animate={{ opacity: 1, y: 0 }}
            className={`verify-step verify-step--${state}`}
            initial={{ opacity: 0, y: 5 }}
            key={step}
            transition={{ duration: 0.2, delay: index * 0.035 }}
          >
            <span aria-hidden="true">{state === 'complete' ? <Check size={14} /> : index + 1}</span>
            <small>{step}</small>
          </motion.li>
        )
      })}
    </ol>
  )
}

function ProfileFields({
  register,
  employmentType,
}: {
  register: ReturnType<typeof useForm<ReviewFormValues>>['register']
  employmentType: ReviewFormValues['employment_type']
}) {
  const amountFields = [
    ...(employmentType === 'employee'
      ? [
          ['salary_components.basic_salary', 'Basic salary'],
          ['salary_components.dearness_allowance', 'Dearness allowance'],
          ['salary_components.hra_received', 'HRA received'],
          ['salary_components.other_allowances', 'Other salary allowances'],
          ['hra_inputs.rent_paid', 'Rent paid'],
        ]
      : []),
    ['other_income', employmentType === 'employee' ? 'Other income' : 'Net business / freelance income'],
    ['deductions_claimed.section_80c', 'Section 80C claimed'],
    ['deductions_claimed.section_80d', 'Section 80D claimed'],
    ['deductions_claimed.section_80ccd_1b', 'Section 80CCD(1B) claimed'],
    ['deductions_claimed.section_80e', 'Section 80E claimed'],
    ['deductions_claimed.section_24b', 'Section 24(b) claimed'],
    ['planning_eligibility.eligible_health_insurance_premium', 'Annual eligible health-insurance premium'],
    ['planning_eligibility.eligible_education_loan_interest', 'Annual eligible education-loan interest'],
    ['planning_eligibility.eligible_home_loan_interest', 'Annual eligible home-loan interest'],
  ] as const

  return (
    <section aria-labelledby="profile-heading" className="verify-profile">
      <div className="verify-section-heading">
        <div>
          <p className="eyebrow">YOUR TAX PROFILE</p>
          <h2 id="profile-heading">Confirm income details</h2>
        </div>
        <span className="verify-edit-note">Amounts in ₹</span>
      </div>
      <div className="verify-profile-grid">
        <label className="verify-input">
          <span>Financial year</span>
          <select {...register('financial_year')}>
            {Array.from({ length: 5 }, (_, index) => {
              const now = new Date()
              const currentStartYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1
              const startYear = currentStartYear - index
              const financialYear = `${startYear}-${String(startYear + 1).slice(-2)}`
              return <option key={financialYear} value={financialYear}>{financialYear}</option>
            })}
          </select>
        </label>
        <label className="verify-input">
          <span>Taxpayer type</span>
          <select {...register('employment_type')}>
            <option value="employee">Employee</option>
            <option value="business_freelancer">Business / freelancer</option>
          </select>
        </label>
        {amountFields.map(([name, label]) => (
          <label className="verify-input" key={name}>
            <span>{label}</span>
            <input inputMode="decimal" type="text" {...register(name as FieldPath<ReviewFormValues>)} />
          </label>
        ))}
        <label className="verify-input">
          <span>Age bracket</span>
          <select {...register('age_bracket')}>
            <option value="below_60">Below 60</option>
            <option value="60_to_79">60–79</option>
            <option value="80_plus">80 or above</option>
          </select>
        </label>
        <label className="verify-input">
          <span>City category for HRA</span>
          <select {...register('city_type')}>
            <option value="metro">Metro</option>
            <option value="non_metro">Non-metro</option>
          </select>
        </label>
      </div>
      <fieldset className="verify-eligibility">
        <legend>Eligibility for additional tax-saving scenarios</legend>
        <p>Confirm only conditions you meet and provide annual eligible amounts from your records. Existing amounts claimed above are not counted twice.</p>
        <label>
          <input type="checkbox" {...register('planning_eligibility.health_insurance_eligible')} />
          <span>I have eligible health-insurance cover/premiums</span>
        </label>
        <label>
          <input type="checkbox" {...register('planning_eligibility.education_loan_eligible')} />
          <span>I have an eligible education loan</span>
        </label>
        <label>
          <input type="checkbox" {...register('planning_eligibility.home_loan_eligible')} />
          <span>I have a qualifying home loan</span>
        </label>
      </fieldset>
      {employmentType === 'business_freelancer' && (
        <p className="verify-note">
          Enter net business or freelance income in the income field. Business-specific tax treatment is not calculated in this prototype.
        </p>
      )}
    </section>
  )
}

function ConsentAndDisclaimer({
  register,
  error,
}: {
  register: ReturnType<typeof useForm<ReviewFormValues>>['register']
  error: string | null
}) {
  return (
    <div className="verify-consent">
      <label>
        <input type="checkbox" {...register('consent_given')} />
        <span>I consent to using these income, deduction, and eligibility details to prepare my tax profile and personalized scenarios.</span>
      </label>
      {error && <p role="alert">{error}</p>}
      <p className="review-disclaimer">FinTax AI provides guidance, not professional tax advice. Verify all information with your source documents and a qualified professional when needed.</p>
    </div>
  )
}

export function ReviewPage() {
  const [params] = useSearchParams()
  const documentId = params.get('documentId')
  const requestedExtractionId = params.get('extractionId')
  const manualMode = params.get('mode') === 'manual'
  const [manualStep, setManualStep] = useState(0)
  const [formErrors, setFormErrors] = useState<string[]>([])
  const queryClient = useQueryClient()
  const form = useForm<ReviewFormValues>({ defaultValues: emptyForm() })
  const employmentType = useWatch({ control: form.control, name: 'employment_type' })
  const extraction = useQuery({
    queryKey: ['document-extraction', documentId],
    queryFn: () => fintaxApi.getDocumentExtraction(documentId!),
    enabled: documentId !== null && !manualMode,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'pending' || status === 'processing' ? 1200 : false
    },
  })
  const extractionId = requestedExtractionId ?? extraction.data?.extraction_id ?? null
  const validation = useQuery({
    queryKey: ['extraction-validation', extractionId],
    queryFn: () => fintaxApi.getExtractionValidation(extractionId!),
    enabled: extractionId !== null && !manualMode,
  })

  const fieldEntries = useMemo(
    () => visibleFields(validation.data?.fields ?? {}),
    [validation.data?.fields],
  )

  useEffect(() => {
    if (manualMode || !validation.data || form.formState.isDirty) return
    const fieldValues = Object.fromEntries(
      fieldEntries.map(([key, field]) => [key.replaceAll('.', '__'), field.value ?? '']),
    )
    form.reset({
      ...emptyForm(),
      field_values: fieldValues,
      salary_components: {
        ...emptyForm().salary_components,
        basic_salary: fieldValues.basic_salary ?? '0',
      },
      other_income: fieldValues.other_income ?? '0',
    })
  }, [fieldEntries, form, manualMode, validation.data])

  const confirmation = useMutation({
    mutationFn: async (values: ReviewFormValues) => {
      const parsed = reviewSchema.safeParse(values)
      if (!parsed.success) {
        setFormErrors(parsed.error.issues.map((issue) => issue.message))
        throw new Error('Review the highlighted form values and consent before continuing.')
      }
      setFormErrors([])
      const profile = buildProfile(parsed.data)
      if (manualMode) return fintaxApi.confirmManualProfile(profile)
      if (!extractionId) throw new Error('The extraction is not ready to confirm.')
      const fieldValues = Object.fromEntries(
        Object.entries(parsed.data.field_values).map(([key, value]) => [
          key.replaceAll('__', '.'),
          value.trim() === '' ? null : value.trim(),
        ]),
      )
      return fintaxApi.confirmExtraction(extractionId, {
        field_values: fieldValues,
        profile,
        consent_given: true,
      })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['user-profile'] })
      if (extractionId) {
        await queryClient.invalidateQueries({ queryKey: ['extraction-validation', extractionId] })
      }
    },
  })

  if (!documentId && !manualMode) {
    return (
      <section className="review-page container">
        <EmptyState
          icon={<FileText aria-hidden="true" size={26} />}
          title="Choose how you’d like to begin."
          description="Upload a tax document for extraction, or enter your information yourself."
          action={(
            <div className="verify-empty-actions">
              <Link className="button button--primary" to="/upload">Upload a document</Link>
              <Link className="button" to="/review?mode=manual">Enter details manually</Link>
            </div>
          )}
        />
      </section>
    )
  }

  if (!manualMode && extraction.isPending && !requestedExtractionId) {
    return (
      <section aria-label="Loading extracted details" className="review-page container">
        <Skeleton className="review-skeleton" />
      </section>
    )
  }

  if (!manualMode && extraction.isError) {
    return (
      <section className="review-page container">
        <p className="upload-error" role="alert">{extraction.error.message}</p>
        <button className="button" onClick={() => void extraction.refetch()} type="button">Retry</button>
      </section>
    )
  }

  if (!manualMode && extraction.data?.status !== 'extracted') {
    return (
      <section className="review-page container">
        <Link className="text-link" to="/upload"><ArrowLeft aria-hidden="true" size={15} /> Back to upload</Link>
        <EmptyState
          icon={<AlertTriangle aria-hidden="true" size={26} />}
          title="Your document is still being read."
          description="This page will show validation checks once extraction is complete."
          action={<Link className="button button--primary" to="/upload">Return to upload</Link>}
        />
      </section>
    )
  }

  if (!manualMode && validation.isError) {
    return (
      <section className="review-page container">
        <p className="upload-error" role="alert">{validation.error.message}</p>
        <button className="button" onClick={() => void validation.refetch()} type="button">Retry validation</button>
      </section>
    )
  }

  if (confirmation.isSuccess) {
    return (
      <section className="review-page container verify-complete">
        <span><CircleCheck aria-hidden="true" size={30} /></span>
        <p className="eyebrow">VERIFICATION COMPLETE</p>
        <h1>Your details are <em>confirmed.</em></h1>
        <p>Your confirmed profile is ready for the next stage. Tax calculations remain unavailable until verified tax rules are configured.</p>
        <Link className="button button--primary" to="/dashboard">Continue to workspace <ArrowRight size={16} /></Link>
      </section>
    )
  }

  const formFields = fieldEntries
  const issues = validation.data?.issues ?? []
  const issueFields = new Map(issues.map((issue) => [issue.field, issue]))
  const consentError = formErrors.find((error) => error.toLowerCase().includes('consent')) ?? null
  const otherFormErrors = formErrors.filter((error) => error !== consentError)
  const isManualChoice = manualMode && manualStep === 0

  return (
    <section className="review-page container">
      <div className="review-page__topline">
        <Link className="text-link" to={manualMode ? '/review' : '/upload'}>
          <ArrowLeft aria-hidden="true" size={15} /> {manualMode ? 'Back to review options' : 'Upload another'}
        </Link>
        <span className="review-status">
          {manualMode ? 'Manual entry' : <><ShieldCheck aria-hidden="true" size={15} /> Private review</>}
        </span>
      </div>
      <WorkflowStepper manualMode={manualMode} />
      <header className="review-heading">
        <p className="eyebrow">{manualMode ? 'VERIFY · MANUAL ENTRY' : 'STEP 03 · VERIFY'}</p>
        <h1>{manualMode ? <>Let’s build your <span>profile.</span></> : <>Take a moment to <span>review.</span></>}</h1>
        <p>
          {manualMode
            ? 'Choose your income path and enter only the details you know.'
            : 'Check every extracted value against the source. Correct anything that needs attention.'}
        </p>
      </header>

      {manualMode ? (
        <form className="verify-form" onSubmit={form.handleSubmit((values) => confirmation.mutate(values))}>
          <AnimatePresence mode="wait">
            {isManualChoice ? (
              <motion.fieldset
                animate={{ opacity: 1, x: 0 }}
                className="manual-choice"
                exit={{ opacity: 0, x: -12 }}
                initial={{ opacity: 0, x: 12 }}
                key="manual-choice"
              >
                <legend>How do you earn income?</legend>
                <label>
                  <input type="radio" value="employee" {...form.register('employment_type')} />
                  <span><strong>Employee</strong><small>Salary, allowances, and rent details</small></span>
                </label>
                <label>
                  <input type="radio" value="business_freelancer" {...form.register('employment_type')} />
                  <span><strong>Business or freelancer</strong><small>Net business or freelance income</small></span>
                </label>
                <button className="button button--primary" onClick={() => setManualStep(1)} type="button">
                  Continue <ArrowRight size={16} />
                </button>
              </motion.fieldset>
            ) : (
              <motion.div
                animate={{ opacity: 1, x: 0 }}
                className="manual-profile"
                exit={{ opacity: 0, x: -12 }}
                initial={{ opacity: 0, x: 12 }}
                key="manual-profile"
              >
                <ProfileFields
                  employmentType={employmentType}
                  register={form.register}
                />
                <ConsentAndDisclaimer register={form.register} error={consentError} />
                {otherFormErrors.length > 0 && (
                  <ul className="verify-form-errors" role="alert">
                    {otherFormErrors.map((error) => <li key={error}>{error}</li>)}
                  </ul>
                )}
                <div className="verify-form-actions">
                  <button className="button" onClick={() => setManualStep(0)} type="button">Back</button>
                  <button className="button button--primary" disabled={confirmation.isPending} type="submit">
                    Confirm profile <Check size={16} />
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          {confirmation.isError && <p className="upload-error" role="alert">{confirmation.error.message}</p>}
        </form>
      ) : (
        <form className="verify-form" onSubmit={form.handleSubmit((values) => confirmation.mutate(values))}>
          {validation.isPending ? (
            <Skeleton className="review-skeleton" />
          ) : validation.data ? (
            <>
              <div className="verify-split">
                <aside aria-label="Original document preview" className="verify-preview">
                  <div className="verify-preview__heading">
                    <span><FileText aria-hidden="true" size={17} /> {validation.data.document_name}</span>
                    <a href={validation.data.preview_url} rel="noreferrer" target="_blank">Open document</a>
                  </div>
                  <iframe title={`Preview of ${validation.data.document_name}`} src={validation.data.preview_url} />
                </aside>
                <div className="verify-fields-panel">
                  <div className="verify-section-heading">
                    <div>
                      <p className="eyebrow">DOCUMENT CHECKS</p>
                      <h2>Review extracted details</h2>
                    </div>
                    <span className="verify-edit-note">Editable</span>
                  </div>
                  {issues.length > 0 && (
                    <div aria-label="Validation issues" className="verify-issues" role="status">
                      {issues.map((issue, index) => (
                        <article className={`verify-issue verify-issue--${issue.severity}`} key={`${issue.field}-${index}`}>
                          <AlertTriangle aria-hidden="true" size={16} />
                          <span><strong>{formatLabel(issue.field)}</strong>{issue.message}<small>{issue.suggested_fix}</small></span>
                        </article>
                      ))}
                    </div>
                  )}
                  <div className="verify-field-list">
                    {formFields.map(([key, field]) => {
                      const issue = issueFields.get(key) ??
                        (key.startsWith('deduction_items.') ? issueFields.get('deduction_items') : undefined)
                      const empty = !field.value?.trim()
                      const state = empty ? 'missing' : issue ? 'flagged' : 'verified'
                      return (
                        <label className={`verify-field verify-field--${state}`} key={key}>
                          <span className="verify-field__top">
                            <strong>{formatLabel(key)}</strong>
                            <small className={`verify-chip verify-chip--${state}`}>{state}</small>
                          </span>
                          <input
                            aria-label={formatLabel(key)}
                            className={
                              issues.some((item) => item.field === key && item.message.includes('confidence'))
                                ? 'verify-field__input verify-field__input--low'
                                : 'verify-field__input'
                            }
                            placeholder={empty ? 'Enter value from the document' : ''}
                            type="text"
                            {...form.register(`field_values.${key.replaceAll('.', '__')}`)}
                          />
                          <span className="verify-field__meta">
                            {Math.round(field.confidence * 100)}% extraction confidence
                            <span>{field.source_page ? `Page ${field.source_page}` : 'Page not identified'}</span>
                          </span>
                        </label>
                      )
                    })}
                  </div>
                  <ProfileFields
                    employmentType={employmentType}
                    register={form.register}
                  />
                  <ConsentAndDisclaimer register={form.register} error={consentError} />
                  {otherFormErrors.length > 0 && (
                    <ul className="verify-form-errors" role="alert">
                      {otherFormErrors.map((error) => <li key={error}>{error}</li>)}
                    </ul>
                  )}
                  {confirmation.isError && <p className="upload-error" role="alert">{confirmation.error.message}</p>}
                  <button
                    className="button button--primary verify-confirm"
                    disabled={confirmation.isPending}
                    type="submit"
                  >
                    {confirmation.isPending ? 'Confirming…' : 'Confirm verified details'}
                    {confirmation.isPending ? null : <Check aria-hidden="true" size={16} />}
                  </button>
                </div>
              </div>
            </>
          ) : null}
        </form>
      )}
    </section>
  )
}
