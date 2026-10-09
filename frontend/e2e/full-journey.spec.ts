import { expect, test } from '@playwright/test'

const userId = '11111111-1111-4111-8111-111111111111'
const documentId = '22222222-2222-4222-8222-222222222222'
const extractionId = '33333333-3333-4333-8333-333333333333'
const sessionId = '44444444-4444-4444-8444-444444444444'
const now = new Date().toISOString()

const taxResult = (regime: 'old' | 'new', tax: string) => ({
  regime,
  act: 'Synthetic test rules — not tax guidance',
  financial_year: '2025-26',
  rules_version: 'synthetic-e2e',
  gross_income: '100000',
  standard_deduction: '0',
  hra_exemption: '0',
  deductions: {},
  taxable_income: '100000',
  tax_before_rebate: tax,
  rebate: '0',
  surcharge: '0',
  cess: '0',
  total_tax: tax,
  trace: [{
    label: 'Total tax',
    formula: 'Synthetic fixture only',
    inputs: {},
    output: tax,
    rule_reference: 'Synthetic E2E fixture',
    plain_language_why: 'This value exists only in a mocked browser test.',
  }],
})

const comparison = {
  old_regime: taxResult('old', '1200'),
  new_regime: taxResult('new', '1000'),
  recommended_regime: 'new',
  saving: '200',
}

test('signup, upload, verify, compare, suggestions, chat and report', async ({ page }) => {
  let savedProfile: Record<string, unknown> | null = null
  let conversationMessages: Array<Record<string, unknown>> = []

  await page.route('**/auth/v1/**', async (route) => {
    const body = {
      access_token: 'synthetic-e2e-access-token',
      token_type: 'bearer',
      expires_in: 3600,
      expires_at: Math.floor(Date.now() / 1000) + 3600,
      refresh_token: 'synthetic-e2e-refresh-token',
      user: {
        id: userId,
        aud: 'authenticated',
        role: 'authenticated',
        email: 'demo@example.test',
        app_metadata: { provider: 'email', providers: ['email'] },
        user_metadata: {},
        created_at: now,
      },
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })
  })

  await page.route('http://127.0.0.1:8000/api/v1/**', async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname.replace('/api/v1', '')
    const method = request.method()
    const json = (body: unknown, status = 200) =>
      route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })

    if (path === '/me' && method === 'GET') {
      return json({
        id: userId,
        email: 'demo@example.test',
        display_name: null,
        preferred_financial_year: null,
        confirmed_profile: savedProfile,
        profile_confirmed_at: savedProfile ? now : null,
        created_at: now,
      })
    }
    if (path === '/documents' && method === 'POST') {
      return json({
        id: documentId,
        file_name: 'synthetic-form16.png',
        content_type: 'image/png',
        size_bytes: 64,
        document_type: 'form16',
        status: 'extracted',
        scan_status: 'clean',
        signed_url: 'https://demo.supabase.co/signed/synthetic',
        signed_url_expires_in: 300,
        auto_delete_at: null,
      }, 202)
    }
    if (path === `/documents/${documentId}/extraction`) {
      return json({
        id: documentId,
        extraction_id: extractionId,
        file_name: 'synthetic-form16.png',
        document_type: 'form16',
        status: 'extracted',
        scan_status: 'clean',
        extraction: {},
        error_code: null,
      })
    }
    if (path === `/extractions/${extractionId}/validation`) {
      const field = (value: string | null) => ({ value, confidence: 0.99, source_page: 1 })
      return json({
        extraction_id: extractionId,
        document_name: 'synthetic-form16.png',
        document_type: 'form16',
        preview_url: 'https://demo.supabase.co/signed/synthetic',
        fields: {
          employee_name: field('Synthetic Demo User'),
          employee_pan: field('AB*******F'),
          employer_name: field('Synthetic Employer'),
          employer_tan: field(''),
          assessment_year: field('2025-26'),
          gross_salary: field('100000'),
          exempt_allowances: field(''),
          perquisites: field(''),
          profits_in_lieu_of_salary: field(''),
          deductions_under_chapter_vi_a: field(''),
          section_80c: field('0'),
          deduction_items: [],
          taxable_income: field('100000'),
          total_tax_deducted: field('0'),
        },
        issues: [],
        is_confirmed: false,
      })
    }
    if (path === `/extractions/${extractionId}/confirm` && method === 'PUT') {
      const body = request.postDataJSON() as { profile: Record<string, unknown> }
      savedProfile = body.profile
      return json({
        extraction_id: extractionId,
        fields: {},
        profile: savedProfile,
        confirmed_at: now,
        issues: [],
      })
    }
    if (path === '/tax/compare' && method === 'POST') {
      return json({ id: '55555555-5555-4555-8555-555555555555', result: comparison })
    }
    if (path === '/tax/suggestions' && method === 'POST') {
      return json({
        financial_year: '2025-26',
        rules_version: 'synthetic-e2e',
        suggestions: [],
        savings_potential: '0',
        planned_count: 0,
      })
    }
    if (path === '/chat/sessions' && method === 'GET') return json([])
    if (path === '/chat/sessions' && method === 'POST') {
      return json({ id: sessionId, title: 'Explain my comparison', created_at: now }, 201)
    }
    if (path === `/chat/sessions/${sessionId}/messages/stream`) {
      conversationMessages = [
        { id: '55555555-5555-4555-8555-555555555555', role: 'user', content: 'Why?', citations: [], created_at: now },
        { id: '66666666-6666-4666-8666-666666666666', role: 'assistant', content: "I'm not sure; the demo uses synthetic data. This is guidance, not professional tax advice.", citations: [], created_at: now },
      ]
      return route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          'event: status\ndata: {"status":"thinking"}\n\n',
          'event: delta\ndata: {"text":"I am not sure; this is a synthetic demo."}\n\n',
          'event: citations\ndata: []\n\n',
          `event: done\ndata: {"message_id":"${conversationMessages[1]?.id}"}\n\n`,
        ].join(''),
      })
    }
    if (path === `/chat/sessions/${sessionId}`) {
      return json({
        session: { id: sessionId, title: 'Explain my comparison', created_at: now },
        messages: conversationMessages,
      })
    }
    if (path === '/reports/latest.pdf') {
      return route.fulfill({
        status: 200,
        contentType: 'application/pdf',
        body: Buffer.from('%PDF-1.4 synthetic e2e report'),
      })
    }
    return json([], 200)
  })

  await page.goto('/signup')
  await page.getByLabel('Email address').fill('demo@example.test')
  await page.getByLabel('Password').fill('synthetic-e2e-password')
  await page.getByRole('button', { name: 'Create account' }).click()
  await expect(page.getByRole('heading', { name: 'Start with your verified tax profile.' })).toBeVisible()
  await page.getByRole('link', { name: 'Upload a document' }).click()

  await page.locator('input[type="file"]').setInputFiles({
    name: 'synthetic-form16.png',
    mimeType: 'image/png',
    buffer: Buffer.from('synthetic fixture'),
  })
  await page.getByRole('button', { name: 'Upload and extract' }).click()
  await expect(page).toHaveURL(/\/review\?/)
  await expect(page.getByRole('heading', { name: 'Take a moment to review.' })).toBeVisible()
  await page.getByRole('checkbox', {
    name: 'I consent to using these income, deduction, and eligibility details to prepare my tax profile and personalized scenarios.',
  }).check()
  await page.getByRole('button', { name: 'Confirm verified details' }).click()
  await expect(page.getByRole('heading', { name: 'Your details are confirmed.' })).toBeVisible()
  await page.getByRole('link', { name: /Continue to workspace/ }).click()
  await expect(page.getByRole('heading', { name: 'A clearer view of your tax.' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Personalized next steps' })).toBeVisible()

  await page.goto('/chat')
  await page.getByLabel('Ask a tax question').fill('Why?')
  await page.getByRole('button', { name: 'Send question' }).click()
  await expect(page.getByText(/I'm not sure; the demo uses synthetic data\./)).toBeVisible()

  await page.goto('/report')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Download PDF' }).click()
  await expect(await download).toBeTruthy()
})
