const workflow = [
  'Upload',
  'Extract',
  'Verify',
  'Calculate',
  'Suggest',
  'Explain & Act',
]

export function HomePage() {
  return (
    <main className="min-h-screen bg-stone-50 text-slate-900">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <a className="text-xl font-bold tracking-tight text-emerald-800" href="/">
          FinTax AI
        </a>
        <span className="rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-medium text-emerald-800">
          Built for clarity
        </span>
      </header>

      <section className="mx-auto max-w-6xl px-6 pb-20 pt-16 sm:pt-24">
        <p className="mb-5 text-sm font-semibold uppercase tracking-[0.18em] text-emerald-700">
          Your taxes, understood
        </p>
        <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-6xl">
          Make confident tax decisions, one clear step at a time.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
          Organize your tax documents and get ready for a transparent,
          explainable tax experience. No calculations are performed in this
          preview.
        </p>
        <button
          className="mt-8 rounded-xl bg-emerald-800 px-5 py-3 font-semibold text-white transition hover:bg-emerald-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-800"
          type="button"
        >
          Get started
        </button>

        <div className="mt-20 rounded-3xl border border-stone-200 bg-white p-6 shadow-sm sm:p-9">
          <p className="text-sm font-semibold text-slate-500">
            A clearer tax journey
          </p>
          <ol className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {workflow.map((step, index) => (
              <li
                className="flex items-center gap-3 rounded-xl bg-stone-50 p-4"
                key={step}
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-semibold text-emerald-800">
                  {index + 1}
                </span>
                <span className="font-medium">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      </section>
    </main>
  )
}
