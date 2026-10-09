import { z } from 'zod'

export class ApiError extends Error {
  readonly status: number
  readonly code: string | undefined

  constructor(message: string, status: number, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'
type AccessTokenProvider = () => Promise<string | null>
let accessTokenProvider: AccessTokenProvider = async () => null
const responseCache = new Map<string, unknown>()
let latestReportBlob: Blob | null = null

export function setApiAccessTokenProvider(provider: AccessTokenProvider): void {
  accessTokenProvider = provider
}

export function clearApiResponseCache(): void {
  responseCache.clear()
  latestReportBlob = null
}

function notifyOfflineFallback(): void {
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('fintax:offline-fallback'))
  }
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase()
  const cacheable = method === 'GET'
  let response: Response
  const token = await accessTokenProvider()
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
    })
  } catch {
    if (cacheable && responseCache.has(path)) {
      notifyOfflineFallback()
      return structuredClone(responseCache.get(path)) as T
    }
    throw new ApiError('Unable to reach FinTax AI. Check your connection and retry.', 0)
  }

  if (!response.ok) {
    if (cacheable && response.status >= 500 && responseCache.has(path)) {
      notifyOfflineFallback()
      return structuredClone(responseCache.get(path)) as T
    }
    let message = `Request failed with status ${response.status}.`
    let code: string | undefined

    try {
      const body: unknown = await response.json()
      if (typeof body === 'object' && body !== null) {
        if ('detail' in body && typeof body.detail === 'string') message = body.detail
        if ('code' in body && typeof body.code === 'string') code = body.code
      }
    } catch {
      // Keep the HTTP status message when the server response has no JSON body.
    }

    throw new ApiError(message, response.status, code)
  }

  if (response.status === 204) {
    if (!cacheable) clearApiResponseCache()
    return undefined as T
  }

  try {
    const payload: unknown = await response.json()
    if (cacheable) responseCache.set(path, payload)
    else clearApiResponseCache()
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('fintax:api-online'))
    }
    return payload as T
  } catch {
    throw new ApiError('The server returned an unreadable response.', response.status)
  }
}

export interface TaxTraceStep {
  label: string
  formula: string
  inputs: Record<string, string | null>
  output: string
  rule_reference: string
  plain_language_why: string
}

export interface TaxResult {
  regime: 'old' | 'new'
  act: string
  financial_year: string
  rules_version: string
  gross_income: string
  standard_deduction: string
  hra_exemption: string
  deductions: Record<string, string>
  taxable_income: string
  tax_before_rebate: string
  rebate: string
  surcharge: string
  cess: string
  total_tax: string
  trace: TaxTraceStep[]
}

export interface TaxComparisonResult {
  old_regime: TaxResult
  new_regime: TaxResult
  recommended_regime: 'old' | 'new'
  saving: string
}

export interface TaxpayerProfileInput {
  salary_components: {
    basic_salary: string
    dearness_allowance: string
    hra_received: string
    other_allowances: string
  }
  hra_inputs: { rent_paid: string }
  other_income: string
  deductions_claimed: {
    section_80c: string
    section_80d: string
    section_80ccd_1b: string
    section_80e: string
    section_24b: string
  }
  age_bracket: 'below_60' | '60_to_79' | '80_plus'
  city_type: 'metro' | 'non_metro'
}

function toTaxpayerProfileInput(profile: TaxpayerProfileInput): TaxpayerProfileInput {
  return {
    salary_components: profile.salary_components,
    hra_inputs: profile.hra_inputs,
    other_income: profile.other_income,
    deductions_claimed: profile.deductions_claimed,
    age_bracket: profile.age_bracket,
    city_type: profile.city_type,
  }
}

export interface DocumentRecord {
  id: string
  file_name: string
  content_type: string
  size_bytes: number
  status: string
  scan_status: string
  created_at: string
}

export interface DocumentUploadResponse extends Omit<DocumentRecord, 'created_at'> {
  signed_url: string
  signed_url_expires_in: number
  auto_delete_at: string | null
}

export interface FilingGuidance {
  status: 'profile_required' | 'guidance_only'
  likely_forms: string[]
  guidance: string
  schedules_to_review: string[]
  documents_to_prepare: string[]
  prefilled_summary: Record<string, unknown> | null
  official_source: string
  disclaimer: string
}

export interface ExtractedField {
  value: string | null
  confidence: number
  source_page: number | null
}

export interface DocumentExtractionResponse {
  id: string
  extraction_id: string | null
  file_name: string
  document_type: 'form16' | 'salary_slip'
  status: 'pending' | 'processing' | 'extracted' | 'failed'
  scan_status: string
  extraction: Record<string, unknown> | null
  error_code: string | null
}

export async function uploadDocument(
  file: File,
  documentType: 'form16' | 'salary_slip',
  onProgress: (percentage: number) => void,
  autoDeleteAfter30Days = false,
): Promise<DocumentUploadResponse> {
  const token = await accessTokenProvider()
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest()
    const form = new FormData()
    form.append('file', file)
    form.append('document_type', documentType)
    form.append('auto_delete_after_30_days', String(autoDeleteAfter30Days))
    request.open('POST', `${API_BASE_URL}/documents`)
    request.timeout = 120_000
    request.setRequestHeader('Accept', 'application/json')
    if (token) request.setRequestHeader('Authorization', `Bearer ${token}`)
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
    request.onload = () => {
      let payload: unknown
      try {
        payload = JSON.parse(request.responseText) as unknown
      } catch {
        reject(new ApiError('The server returned an unreadable response.', request.status))
        return
      }
      if (request.status < 200 || request.status >= 300) {
        const detail =
          typeof payload === 'object' && payload !== null && 'detail' in payload &&
          typeof payload.detail === 'string'
            ? payload.detail
            : `Upload failed with status ${request.status}.`
        const code =
          typeof payload === 'object' && payload !== null && 'code' in payload &&
          typeof payload.code === 'string'
            ? payload.code
            : undefined
        reject(new ApiError(detail, request.status, code))
        return
      }
      const validated = documentUploadSchema.safeParse(payload)
      if (!validated.success) {
        reject(new ApiError('The server returned an invalid upload response.', request.status))
        return
      }
      clearApiResponseCache()
      resolve(validated.data)
    }
    request.onerror = () => reject(new ApiError('Unable to reach FinTax AI. Check your connection and retry.', 0))
    request.ontimeout = () => reject(new ApiError('The upload took too long. Please retry.', 0))
    request.onabort = () => reject(new ApiError('The upload was cancelled.', 0))
    request.send(form)
  })
}

export interface ValidationIssue {
  severity: 'error' | 'warning' | 'info'
  field: string
  message: string
  suggested_fix: string
}

export interface ConfirmedTaxpayerProfile extends TaxpayerProfileInput {
  employment_type: 'employee' | 'business_freelancer'
  consent_given: true
  financial_year: string
  planning_eligibility: {
    health_insurance_eligible: boolean
    eligible_health_insurance_premium: string
    education_loan_eligible: boolean
    eligible_education_loan_interest: string
    home_loan_eligible: boolean
    eligible_home_loan_interest: string
  }
}

export interface Suggestion {
  id: string
  key: string
  title: string
  product: string
  amount_to_invest: string
  lock_in_period: string
  liquidity_note: string
  tax_saved: string
  net_benefit: string
  eligible_regime: 'old' | 'new' | null
  alternative_group: string | null
  rule_reference: string
  explanation: string
  explanation_source: 'gemini' | 'template'
  before: TaxComparisonResult
  after: TaxComparisonResult
  planned_to_do: boolean
}

export interface TaxSuggestions {
  financial_year: string
  rules_version: string
  suggestions: Suggestion[]
  savings_potential: string
  planned_count: number
}

export interface SimulationResult {
  financial_year: string
  rules_version: string
  before: TaxComparisonResult
  after: TaxComparisonResult
  tax_saved: string
  recommended_regime_changed: boolean
  trace_before: TaxTraceStep[]
  trace_after: TaxTraceStep[]
}

export interface ChatCitation {
  source: string
  section: string
  link: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations: ChatCitation[]
  created_at: string
}

export interface ChatSession {
  id: string
  title: string | null
  created_at: string
}

export interface ChatHistory {
  session: ChatSession
  messages: ChatMessage[]
}

export type ChatStreamEvent =
  | { type: 'status' }
  | { type: 'delta'; text: string }
  | { type: 'citations'; citations: ChatCitation[] }
  | { type: 'done'; messageId: string }
  | { type: 'error'; message: string }

export interface ExtractionValidationResponse {
  extraction_id: string
  document_name: string
  document_type: 'form16' | 'salary_slip'
  preview_url: string
  fields: Record<string, unknown>
  issues: ValidationIssue[]
  is_confirmed: boolean
}

const documentUploadSchema = z.object({
  id: z.uuid(),
  file_name: z.string(),
  content_type: z.string(),
  size_bytes: z.number().int().nonnegative(),
  document_type: z.enum(['form16', 'salary_slip']),
  status: z.enum(['pending', 'processing', 'extracted', 'failed']),
  scan_status: z.string(),
  signed_url: z.url(),
  signed_url_expires_in: z.number().int().positive(),
  auto_delete_at: z.string().nullable(),
})

const filingGuidanceSchema = z.object({
  status: z.enum(['profile_required', 'guidance_only']),
  likely_forms: z.array(z.string()),
  guidance: z.string(),
  schedules_to_review: z.array(z.string()),
  documents_to_prepare: z.array(z.string()),
  prefilled_summary: z.record(z.string(), z.unknown()).nullable(),
  official_source: z.url(),
  disclaimer: z.string(),
})

const documentExtractionSchema = z.object({
  id: z.uuid(),
  extraction_id: z.uuid().nullable(),
  file_name: z.string(),
  document_type: z.enum(['form16', 'salary_slip']),
  status: z.enum(['pending', 'processing', 'extracted', 'failed']),
  scan_status: z.string(),
  extraction: z.record(z.string(), z.unknown()).nullable(),
  error_code: z.string().nullable(),
})

const validationIssueSchema = z.object({
  severity: z.enum(['error', 'warning', 'info']),
  field: z.string(),
  message: z.string(),
  suggested_fix: z.string(),
})

const extractionValidationSchema = z.object({
  extraction_id: z.uuid(),
  document_name: z.string(),
  document_type: z.enum(['form16', 'salary_slip']),
  preview_url: z.url(),
  fields: z.record(z.string(), z.unknown()),
  issues: z.array(validationIssueSchema),
  is_confirmed: z.boolean(),
})

const confirmedTaxpayerProfileSchema = z.object({
  employment_type: z.enum(['employee', 'business_freelancer']),
  consent_given: z.literal(true),
  financial_year: z.string().regex(/^\d{4}-\d{2}$/),
  salary_components: z.object({
    basic_salary: z.string(),
    dearness_allowance: z.string(),
    hra_received: z.string(),
    other_allowances: z.string(),
  }),
  hra_inputs: z.object({ rent_paid: z.string() }),
  other_income: z.string(),
  deductions_claimed: z.object({
    section_80c: z.string(),
    section_80d: z.string(),
    section_80ccd_1b: z.string(),
    section_80e: z.string(),
    section_24b: z.string(),
  }),
  age_bracket: z.enum(['below_60', '60_to_79', '80_plus']),
  city_type: z.enum(['metro', 'non_metro']),
  planning_eligibility: z.object({
    health_insurance_eligible: z.boolean(),
    eligible_health_insurance_premium: z.string(),
    education_loan_eligible: z.boolean(),
    eligible_education_loan_interest: z.string(),
    home_loan_eligible: z.boolean(),
    eligible_home_loan_interest: z.string(),
  }),
})

const userProfileSchema = z.object({
  id: z.string(),
  email: z.string().nullable(),
  confirmed_profile: confirmedTaxpayerProfileSchema.nullable(),
})

const taxTraceStepSchema = z.object({
  label: z.string(),
  formula: z.string(),
  inputs: z.record(z.string(), z.string().nullable()),
  output: z.string(),
  rule_reference: z.string(),
  plain_language_why: z.string(),
})

const taxResultSchema = z.object({
  regime: z.enum(['old', 'new']),
  act: z.string(),
  financial_year: z.string(),
  rules_version: z.string(),
  gross_income: z.string(),
  standard_deduction: z.string(),
  hra_exemption: z.string(),
  deductions: z.record(z.string(), z.string()),
  taxable_income: z.string(),
  tax_before_rebate: z.string(),
  rebate: z.string(),
  surcharge: z.string(),
  cess: z.string(),
  total_tax: z.string(),
  trace: z.array(taxTraceStepSchema),
})

const taxComparisonResponseSchema = z.object({
  id: z.uuid(),
  result: z.object({
    old_regime: taxResultSchema,
    new_regime: taxResultSchema,
    recommended_regime: z.enum(['old', 'new']),
    saving: z.string(),
  }),
})

const suggestionSchema = z.object({
  id: z.uuid(),
  key: z.string(),
  title: z.string(),
  product: z.string(),
  amount_to_invest: z.string(),
  lock_in_period: z.string(),
  liquidity_note: z.string(),
  tax_saved: z.string(),
  net_benefit: z.string(),
  eligible_regime: z.enum(['old', 'new']).nullable(),
  alternative_group: z.string().nullable(),
  rule_reference: z.string(),
  explanation: z.string(),
  explanation_source: z.enum(['gemini', 'template']),
  before: taxComparisonResponseSchema.shape.result,
  after: taxComparisonResponseSchema.shape.result,
  planned_to_do: z.boolean(),
})

const taxSuggestionsSchema = z.object({
  financial_year: z.string(),
  rules_version: z.string(),
  suggestions: z.array(suggestionSchema),
  savings_potential: z.string(),
  planned_count: z.number().int().nonnegative(),
})

const simulationSchema = z.object({
  financial_year: z.string(),
  rules_version: z.string(),
  before: taxComparisonResponseSchema.shape.result,
  after: taxComparisonResponseSchema.shape.result,
  tax_saved: z.string(),
  recommended_regime_changed: z.boolean(),
  trace_before: z.array(taxTraceStepSchema),
  trace_after: z.array(taxTraceStepSchema),
})

const chatCitationSchema = z.object({
  source: z.string(),
  section: z.string(),
  link: z.url(),
})

const chatMessageSchema = z.object({
  id: z.uuid(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  citations: z.array(chatCitationSchema),
  created_at: z.string(),
})

const chatSessionSchema = z.object({
  id: z.uuid(),
  title: z.string().nullable(),
  created_at: z.string(),
})

const chatHistorySchema = z.object({
  session: chatSessionSchema,
  messages: z.array(chatMessageSchema),
})

const chatSessionsSchema = z.array(chatSessionSchema)

export async function streamChatMessage(
  sessionId: string,
  content: string,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const token = await accessTokenProvider()
  const headers = new Headers({
    Accept: 'text/event-stream',
    'Content-Type': 'application/json',
  })
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(
      `${API_BASE_URL}/chat/sessions/${encodeURIComponent(sessionId)}/messages/stream`,
      { method: 'POST', headers, body: JSON.stringify({ content }) },
    )
  } catch {
    throw new ApiError('Unable to reach FinTax AI. Check your connection and retry.', 0)
  }
  if (!response.ok) {
    let message = `Request failed with status ${response.status}.`
    try {
      const body: unknown = await response.json()
      if (typeof body === 'object' && body !== null && 'detail' in body &&
        typeof body.detail === 'string') message = body.detail
    } catch {
      // Retain the HTTP status when the server did not return JSON.
    }
    throw new ApiError(message, response.status)
  }
  if (!response.body) throw new ApiError('The server did not start a chat stream.', response.status)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finished = false
  while (!finished) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary).replaceAll('\r', '')
      buffer = buffer.slice(boundary + 2)
      const lines = block.split('\n')
      const eventName = lines.find((line) => line.startsWith('event:'))?.slice(6).trim()
      const data = lines
        .filter((line) => line.startsWith('data:'))
        .map((line) => line.slice(5).trimStart())
        .join('\n')
      if (eventName && data) {
        const payload: unknown = JSON.parse(data)
        if (eventName === 'status') onEvent({ type: 'status' })
        if (eventName === 'delta' && typeof payload === 'object' && payload !== null &&
          'text' in payload && typeof payload.text === 'string') {
          onEvent({ type: 'delta', text: payload.text })
        }
        if (eventName === 'citations') {
          onEvent({
            type: 'citations',
            citations: z.array(chatCitationSchema).parse(payload),
          })
        }
        if (eventName === 'done' && typeof payload === 'object' && payload !== null &&
          'message_id' in payload && typeof payload.message_id === 'string') {
          onEvent({ type: 'done', messageId: payload.message_id })
        }
        if (eventName === 'error' && typeof payload === 'object' && payload !== null &&
          'message' in payload && typeof payload.message === 'string') {
          onEvent({ type: 'error', message: payload.message })
          finished = true
        }
      }
      boundary = buffer.indexOf('\n\n')
    }
    if (done) finished = true
  }
  await reader.cancel()
}

export const fintaxApi = {
  getProfile: async () => userProfileSchema.parse(await apiRequest<unknown>('/me')),
  confirmManualProfile: async (profile: ConfirmedTaxpayerProfile) =>
    apiRequest<ConfirmedTaxpayerProfile>('/me/confirmed-profile', {
      method: 'PUT',
      body: JSON.stringify(profile),
    }),
  listDocuments: () => apiRequest<DocumentRecord[]>('/documents'),
  uploadDocument,
  getDocumentExtraction: async (documentId: string) =>
    documentExtractionSchema.parse(
      await apiRequest<unknown>(`/documents/${encodeURIComponent(documentId)}/extraction`),
    ),
  getExtractionValidation: async (extractionId: string) =>
    extractionValidationSchema.parse(
      await apiRequest<unknown>(
        `/extractions/${encodeURIComponent(extractionId)}/validation`,
      ),
    ),
  confirmExtraction: async (
    extractionId: string,
    request: {
      field_values: Record<string, string | null>
      profile: ConfirmedTaxpayerProfile
      consent_given: true
    },
  ) =>
    apiRequest<{
      extraction_id: string
      fields: Record<string, ExtractedField>
      profile: ConfirmedTaxpayerProfile
      confirmed_at: string
      issues: ValidationIssue[]
    }>(`/extractions/${encodeURIComponent(extractionId)}/confirm`, {
      method: 'PUT',
      body: JSON.stringify(request),
    }),
  retryDocumentExtraction: async (documentId: string) =>
    documentExtractionSchema.parse(
      await apiRequest<unknown>(`/documents/${encodeURIComponent(documentId)}/retry`, {
        method: 'POST',
      }),
    ),
  computeTax: (request: {
    financial_year: string
    regime: 'old' | 'new'
    profile: TaxpayerProfileInput
  }) => apiRequest<{ id: string; result: TaxResult }>('/tax/compute', {
    method: 'POST',
    body: JSON.stringify(request),
  }),
  compareTax: async (request: { financial_year: string; profile: TaxpayerProfileInput }) =>
    taxComparisonResponseSchema.parse(await apiRequest<unknown>('/tax/compare', {
      method: 'POST',
      body: JSON.stringify({
        ...request,
        profile: toTaxpayerProfileInput(request.profile),
      }),
    })),
  getSuggestions: async (profile: ConfirmedTaxpayerProfile) =>
    taxSuggestionsSchema.parse(await apiRequest<unknown>('/tax/suggestions', {
      method: 'POST',
      body: JSON.stringify({
        financial_year: profile.financial_year,
        profile,
      }),
    })),
  setSuggestionPlanned: (suggestionId: string, plannedToDo: boolean) =>
    apiRequest<{ id: string; key: string; planned_to_do: boolean }>(
      `/tax/suggestions/${encodeURIComponent(suggestionId)}/plan`,
      {
        method: 'PUT',
        body: JSON.stringify({ planned_to_do: plannedToDo }),
      },
    ),
  simulateTax: async (request: {
    financial_year: string
    profile: TaxpayerProfileInput
    change: { kind: 'deduction'; section: '80C' | '80D' | '80CCD(1B)' | '80E' | '24B'; amount: string }
      | { kind: 'rent'; amount: string }
  }) =>
    simulationSchema.parse(await apiRequest<unknown>('/tax/simulate', {
      method: 'POST',
    body: JSON.stringify({
      ...request,
      profile: toTaxpayerProfileInput(request.profile),
    }),
  })),
  listChatSessions: async () =>
  chatSessionsSchema.parse(await apiRequest<unknown>('/chat/sessions')),
  createChatSession: async (title?: string) =>
  chatSessionSchema.parse(await apiRequest<unknown>('/chat/sessions', {
    method: 'POST',
    body: JSON.stringify(title ? { title } : {}),
  })),
  getChatHistory: async (sessionId: string) =>
  chatHistorySchema.parse(
    await apiRequest<unknown>(`/chat/sessions/${encodeURIComponent(sessionId)}`),
  ),
  getFilingGuidance: async () =>
    filingGuidanceSchema.parse(await apiRequest<unknown>('/filing-guidance')),
  downloadLatestReport: async () => {
    const token = await accessTokenProvider()
    const headers = new Headers({ Accept: 'application/pdf' })
    if (token) headers.set('Authorization', `Bearer ${token}`)
    let response: Response
    try {
      response = await fetch(`${API_BASE_URL}/reports/latest.pdf`, { headers })
    } catch {
      if (latestReportBlob) {
        notifyOfflineFallback()
        return latestReportBlob.slice()
      }
      throw new ApiError('Unable to reach FinTax AI. Check your connection and retry.', 0)
    }
    if (!response.ok) {
      if (response.status >= 500 && latestReportBlob) {
        notifyOfflineFallback()
        return latestReportBlob.slice()
      }
      let message = `Request failed with status ${response.status}.`
      try {
        const body: unknown = await response.json()
        if (typeof body === 'object' && body !== null && 'detail' in body &&
          typeof body.detail === 'string') message = body.detail
      } catch {
        // Keep the status message if a PDF error response was not JSON.
      }
      throw new ApiError(message, response.status)
    }
    latestReportBlob = await response.blob()
    return latestReportBlob.slice()
  },
  deleteMyData: () => apiRequest<void>('/me/data', {
    method: 'DELETE',
    body: JSON.stringify({ confirmation: 'DELETE' }),
  }),
}
