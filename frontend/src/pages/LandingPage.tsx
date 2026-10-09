import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BookOpenCheck,
  FileCheck2,
  FileSpreadsheet,
  Fingerprint,
  LockKeyhole,
  Scale,
  ShieldCheck,
  Sparkles,
  WalletCards,
  Zap,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { CountUp } from '../components/motion/CountUp'
import { MagneticButton } from '../components/motion/MagneticButton'
import { Reveal } from '../components/motion/Reveal'
import { Stagger, StaggerItem } from '../components/motion/Stagger'
import { formatINR } from '../lib/formatters'

const TaxScene = lazy(async () => {
  const { TaxScene: Scene } = await import('../components/hero/TaxScene')
  return { default: Scene }
})

const trustStripItems = [
  {
    icon: ShieldCheck,
    title: 'Bank-Grade Security',
    description: '256-bit AES encryption at rest & in transit',
  },
  {
    icon: Fingerprint,
    title: 'Data Stays Yours',
    description: 'Zero AI model training on your financial records',
  },
  {
    icon: BookOpenCheck,
    title: 'Grounded in Law',
    description: 'IT Act Sections 80C, 80D, 87A & 115BAC citations',
  },
  {
    icon: BadgeCheck,
    title: 'AY 2025-26 & 2026-27',
    description: 'Latest budget slabs & standard deduction rules',
  },
]

const steps = [
  {
    number: '01',
    title: 'Upload Documents',
    description:
      'Drop your Form 16, salary slips, or AIS in one private, encrypted workspace.',
    icon: WalletCards,
  },
  {
    number: '02',
    title: 'Understand & Validate',
    description:
      'Review parsed data, verify TDS deductions, and check section-by-section breakdown.',
    icon: FileCheck2,
  },
  {
    number: '03',
    title: 'Optimize & File',
    description:
      'Compare Old vs New regime live, uncover missed deductions, and download audit-ready report.',
    icon: Sparkles,
  },
]

const features = [
  {
    title: 'Smart Form 16 Extraction',
    description:
      'Auto-parses Part A & Part B, salary slips, and investment proofs with field-level confidence tags.',
    icon: FileSpreadsheet,
    tone: 'blue',
  },
  {
    title: 'Dual Regime Optimizer',
    description:
      'Instant side-by-side tax liability under Section 115BAC vs Old Regime with dynamic savings alerts.',
    icon: Scale,
    tone: 'green',
  },
  {
    title: 'Deduction Finder',
    description:
      'Discover eligible deductions across 80C, 80CCD(1B) NPS, 80D health insurance, HRA, and home loan interest.',
    icon: Zap,
    tone: 'amber',
  },
  {
    title: 'Filing Readiness Score',
    description:
      'Real-time automated audit checks flagging PAN mismatches, TDS discrepancies, or missing proofs.',
    icon: BadgeCheck,
    tone: 'blue',
  },
  {
    title: 'Official Sources Cited',
    description:
      'Every number and recommendation links directly to Income Tax Department circulars and sections.',
    icon: BookOpenCheck,
    tone: 'green',
  },
  {
    title: 'Client-Side Privacy',
    description:
      'Your documents are processed securely with optional auto-delete and zero external data sharing.',
    icon: LockKeyhole,
    tone: 'amber',
  },
]

interface NavigatorWithDeviceMemory extends Navigator {
  deviceMemory?: number
}

function canRenderScene() {
  if (typeof navigator === 'undefined' || typeof window === 'undefined') {
    return false
  }
  const device = navigator as NavigatorWithDeviceMemory
  const lowMemory = device.deviceMemory !== undefined && device.deviceMemory <= 4
  const lowCpu =
    navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency <= 4
  const smallScreen = window.matchMedia('(max-width: 760px)').matches
  return !lowMemory && !lowCpu && !smallScreen
}

function HeroArtwork() {
  const [reducedMotion, setReducedMotion] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
      : false,
  )
  const [sceneReady, setSceneReady] = useState(false)
  const showScene = !reducedMotion && canRenderScene()

  useEffect(() => {
    const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
    const updatePreference = (event: MediaQueryListEvent) => {
      setReducedMotion(event.matches)
    }
    preference.addEventListener('change', updatePreference)
    return () => preference.removeEventListener('change', updatePreference)
  }, [])

  useEffect(() => {
    if (!showScene) return
    const timeoutId = window.setTimeout(() => setSceneReady(true), 1200)
    return () => window.clearTimeout(timeoutId)
  }, [showScene])

  return (
    <div className="hero-art" aria-label="Visual preview of FinTax AI workspace">
      <div className="hero-art__glow" aria-hidden="true" />

      {/* 3D WebGL Canvas or Fallback */}
      {showScene && sceneReady ? (
        <>
          <Suspense fallback={<div className="scene-fallback" aria-hidden="true" />}>
            <div className="hero-art__canvas">
              <TaxScene />
            </div>
          </Suspense>
          <span className="scene-currency" aria-hidden="true">
            ₹
          </span>
        </>
      ) : (
        <div className="scene-fallback" aria-hidden="true">
          <span className="scene-fallback__coin">₹</span>
          <span className="scene-fallback__document" />
          <span className="scene-fallback__chart" />
        </div>
      )}

      {/* Workspace Preview Card Overlay */}
      <div className="workspace-card">
        <div className="workspace-card__top">
          <div>
            <span className="workspace-card__eyebrow">TAX WORKSPACE PREVIEW</span>
            <h2>Everything, in one place.</h2>
          </div>
          <span className="workspace-card__status">
            <span /> Active
          </span>
        </div>
        <div className="workspace-card__files">
          <div className="file-row">
            <span className="file-row__icon file-row__icon--blue">
              <FileCheck2 aria-hidden="true" size={18} />
            </span>
            <span className="file-row__details">
              <strong>Form 16 (Part A & B)</strong>
              <small>Verified with 100% confidence</small>
            </span>
            <BadgeCheck className="file-row__check" aria-hidden="true" size={18} />
          </div>
          <div className="file-row">
            <span className="file-row__icon file-row__icon--green">
              <WalletCards aria-hidden="true" size={18} />
            </span>
            <span className="file-row__details">
              <strong>New Regime Optimizer</strong>
              <small>Section 115BAC recommended</small>
            </span>
            <ArrowUpRight className="file-row__arrow" aria-hidden="true" size={17} />
          </div>
        </div>
        <div className="workspace-card__foot">
          <span>
            <LockKeyhole aria-hidden="true" size={13} /> Private by design
          </span>
          <span>AY 2025-26</span>
        </div>
      </div>

      <div className="float-note float-note--source">
        <span className="float-note__icon">
          <BookOpenCheck aria-hidden="true" size={16} />
        </span>
        <span>
          <strong>IT Act Grounded</strong>
          <small>Section citations included</small>
        </span>
      </div>
      <div className="float-note float-note--trace">
        <span className="float-note__icon float-note__icon--green">
          <BadgeCheck aria-hidden="true" size={16} />
        </span>
        <span>
          <strong>Audit-Ready</strong>
          <small>Zero guesswork calculations</small>
        </span>
      </div>
    </div>
  )
}

/**
 * Interactive Dual Regime Optimizer teaser.
 * Simulates Indian tax brackets for AY 2025-26 / 2026-27.
 */
function RegimeSimulatorTeaser() {
  const navigate = useNavigate()
  const [salary, setSalary] = useState(1500000)

  const { taxNew, taxOld, savings } = useMemo(() => {
    // New Regime (Sec 115BAC: Std Deduction ₹75,000)
    const stdDedNew = 75000
    const taxableNew = Math.max(0, salary - stdDedNew)
    let baseTaxNew = 0
    if (taxableNew <= 700000) {
      baseTaxNew = 0 // Rebate u/s 87A
    } else {
      if (taxableNew > 300000)
        baseTaxNew += Math.min(taxableNew - 300000, 400000) * 0.05
      if (taxableNew > 700000)
        baseTaxNew += Math.min(taxableNew - 700000, 300000) * 0.1
      if (taxableNew > 1000000)
        baseTaxNew += Math.min(taxableNew - 1000000, 200000) * 0.15
      if (taxableNew > 1200000)
        baseTaxNew += Math.min(taxableNew - 1200000, 300000) * 0.2
      if (taxableNew > 1500000) baseTaxNew += (taxableNew - 1500000) * 0.3
    }
    const computedTaxNew = Math.round(baseTaxNew * 1.04)

    // Old Regime (Std Deduction ₹50,000 + ₹1.5L 80C + ₹25k 80D typical)
    const deductionsOld = 50000 + 150000 + 25000
    const taxableOld = Math.max(0, salary - deductionsOld)
    let baseTaxOld = 0
    if (taxableOld <= 500000) {
      baseTaxOld = 0 // Rebate u/s 87A
    } else {
      if (taxableOld > 250000)
        baseTaxOld += Math.min(taxableOld - 250000, 250000) * 0.05
      if (taxableOld > 500000)
        baseTaxOld += Math.min(taxableOld - 500000, 500000) * 0.2
      if (taxableOld > 1000000) baseTaxOld += (taxableOld - 1000000) * 0.3
    }
    const computedTaxOld = Math.round(baseTaxOld * 1.04)

    const taxSavings = Math.max(0, computedTaxOld - computedTaxNew)
    return { taxNew: computedTaxNew, taxOld: computedTaxOld, savings: taxSavings }
  }, [salary])

  return (
    <section className="product-preview-section section-pad" id="simulator-preview">
      <div className="container">
        <Reveal className="section-heading">
          <p className="eyebrow">Dual Regime Optimizer</p>
          <h2>
            See your savings <span>before you file.</span>
          </h2>
          <p>
            Slide to your approximate annual income to preview Old vs New Regime
            under Section 115BAC.
          </p>
        </Reveal>

        <div className="preview-card">
          <div className="preview-card__header">
            <div>
              <span className="preview-card__badge">
                <Sparkles size={14} /> LIVE TAX CALCULATOR
              </span>
              <h3 style={{ margin: '0.4rem 0 0', fontSize: '1.2rem', fontWeight: 700 }}>
                AY 2025-26 & 2026-27 Comparison
              </h3>
            </div>
            <MagneticButton
              className="button button--small button--primary"
              onClick={() => navigate('/simulator')}
              type="button"
            >
              Open Full Simulator <ArrowUpRight size={15} />
            </MagneticButton>
          </div>

          <div className="preview-card__content">
            {/* Interactive Salary Slider */}
            <div className="preview-slider-box">
              <div className="preview-slider-top">
                <label htmlFor="salary-range">Annual Gross Salary</label>
                <div className="preview-slider-value">{formatINR(salary)}</div>
              </div>
              <input
                aria-label="Annual Gross Salary slider"
                className="preview-range-input"
                id="salary-range"
                max={4000000}
                min={600000}
                onChange={(e) => setSalary(Number(e.target.value))}
                step={50000}
                type="range"
                value={salary}
              />
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginTop: '0.5rem',
                  fontSize: '0.74rem',
                  color: 'var(--text-muted)',
                }}
              >
                <span>₹6 Lakhs</span>
                <span>₹20 Lakhs</span>
                <span>₹40 Lakhs</span>
              </div>
            </div>

            {/* Side-by-side comparison */}
            <div className="preview-regimes-grid">
              {/* New Regime (Recommended) */}
              <div className="preview-regime-card preview-regime-card--winner">
                <div className="preview-regime-card__top">
                  <h4>New Regime (Sec 115BAC)</h4>
                  <span className="preview-regime-card__tag">Recommended</span>
                </div>
                <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Estimated Tax Liability
                </p>
                <div className="preview-tax-amount">
                  <CountUp value={taxNew} />
                </div>
                <div className="preview-breakdown">
                  <div className="preview-breakdown-row">
                    <span>Standard Deduction</span>
                    <span>₹75,000</span>
                  </div>
                  <div className="preview-breakdown-row">
                    <span>Tax Slabs</span>
                    <span>Concessional Slabs</span>
                  </div>
                  <div className="preview-breakdown-row">
                    <span>Rebate u/s 87A</span>
                    <span>Up to ₹7L income</span>
                  </div>
                </div>
              </div>

              {/* Old Regime */}
              <div className="preview-regime-card">
                <div className="preview-regime-card__top">
                  <h4>Old Regime</h4>
                  <span className="preview-regime-card__tag">With Deductions</span>
                </div>
                <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Estimated Tax Liability
                </p>
                <div className="preview-tax-amount">
                  <CountUp value={taxOld} />
                </div>
                <div className="preview-breakdown">
                  <div className="preview-breakdown-row">
                    <span>Standard Deduction</span>
                    <span>₹50,000</span>
                  </div>
                  <div className="preview-breakdown-row">
                    <span>80C & 80D Allowed</span>
                    <span>Up to ₹1,75,000</span>
                  </div>
                  <div className="preview-breakdown-row">
                    <span>Rebate u/s 87A</span>
                    <span>Up to ₹5L income</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Dynamic Savings Banner */}
            <div className="preview-savings-banner">
              <strong>
                <Sparkles size={20} />
                {savings > 0 ? (
                  <>You save {formatINR(savings)} under the New Regime!</>
                ) : (
                  <>Old Regime is competitive with heavy deductions.</>
                )}
              </strong>
              <button
                className="button button--small button--primary"
                onClick={() => navigate('/upload')}
                type="button"
              >
                Upload Form 16 to Optimize <ArrowRight size={15} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

export function LandingPage() {
  const navigate = useNavigate()

  return (
    <>
      {/* 1. Hero Section */}
      <section className="hero-section">
        <div className="hero-container">
          <div className="hero-copy">
            <Reveal>
              <p className="eyebrow">
                <span className="eyebrow__spark" /> AI-Powered Tax Intelligence for
                India
              </p>
              <h1>
                Your taxes,
                <br />
                <span className="headline-accent">without the</span>
                <br />
                <span className="headline-serif">guesswork.</span>
              </h1>
              <p className="hero-copy__description">
                Upload your Form 16, salary slips, or investment proofs. FinTax AI
                extracts, validates against IT Act rules, calculates your optimal
                regime, and gives you audit-ready filing guidance in seconds.
              </p>
              <div className="hero-copy__actions">
                <MagneticButton
                  className="button button--primary"
                  onClick={() => navigate('/upload')}
                  type="button"
                >
                  Upload Documents <ArrowUpRight aria-hidden="true" size={17} />
                </MagneticButton>
                <button
                  className="button button--light"
                  onClick={() => navigate('/simulator')}
                  type="button"
                >
                  Try Tax Simulator <ArrowRight aria-hidden="true" size={16} />
                </button>
                <a className="text-link" href="#how-it-works">
                  See how it works <ArrowDown aria-hidden="true" size={15} />
                </a>
              </div>
              <div className="hero-trust">
                <span>
                  <LockKeyhole aria-hidden="true" size={14} /> 100% Client-Side Privacy
                </span>
                <span className="hero-trust__divider" aria-hidden="true" />
                <span>AY 2025-26 & 2026-27 Compliant</span>
              </div>
            </Reveal>
          </div>

          {/* Interactive 3D Hero Artwork */}
          <HeroArtwork />
        </div>

        <div className="hero-bottom container">
          <span className="hero-bottom__label">
            LESS PAPERWORK. MAXIMUM TAX SAVINGS. AUDIT-READY CONFIDENCE.
          </span>
          <a href="#trust-strip">
            Scroll to explore <ArrowDown aria-hidden="true" size={14} />
          </a>
        </div>
      </section>

      {/* 2. Trust Strip (4-badge row) */}
      <section className="trust-strip" id="trust-strip">
        <div className="trust-strip__inner">
          {trustStripItems.map(({ icon: Icon, title, description }) => (
            <div className="trust-strip__item" key={title}>
              <div className="trust-strip__icon">
                <Icon size={18} />
              </div>
              <div>
                <strong>{title}</strong>
                <span>{description}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 3. Product Preview / Regime Simulator Teaser */}
      <RegimeSimulatorTeaser />

      {/* 4. Journey / How it works */}
      <section className="journey-section section-pad" id="how-it-works">
        <div className="container">
          <Reveal className="section-heading">
            <p className="eyebrow">A better kind of tax season</p>
            <h2>
              Three steps to <span>feeling in control.</span>
            </h2>
            <p>From a pile of paperwork to an optimized plan that makes complete sense.</p>
          </Reveal>
          <div className="journey-grid">
            {steps.map(({ number, title, description, icon: Icon }, index) => (
              <Reveal
                className={`journey-step journey-step--${index + 1}`}
                delay={index * 0.1}
                key={number}
              >
                <div className="journey-step__top">
                  <span className="journey-step__number">{number}</span>
                  <span className="journey-step__icon">
                    <Icon aria-hidden="true" size={21} />
                  </span>
                </div>
                <h3>{title}</h3>
                <p>{description}</p>
                {index < steps.length - 1 && (
                  <span className="journey-step__connector" aria-hidden="true" />
                )}
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* 5. Features Grid (6 cards) */}
      <section className="features-section section-pad" id="features">
        <div className="container">
          <Reveal className="features-intro">
            <div>
              <p className="eyebrow">Confidence, built in</p>
              <h2>
                Not just answers.
                <br />
                <span>Answers you can trust.</span>
              </h2>
            </div>
            <p>
              Every calculation is mathematically verified against the latest Indian
              Income Tax Act provisions.
            </p>
          </Reveal>
          <Stagger className="feature-grid">
            {features.map(({ title, description, icon: Icon, tone }) => (
              <StaggerItem className="feature-card" key={title}>
                <span className={`feature-card__icon feature-card__icon--${tone}`}>
                  <Icon aria-hidden="true" size={22} />
                </span>
                <h3>{title}</h3>
                <p>{description}</p>
                <span className="feature-card__arrow" aria-hidden="true">
                  <ArrowRight size={17} />
                </span>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </section>

      {/* 6. Trust Section */}
      <section className="trust-section section-pad" id="trust">
        <div className="container trust-panel">
          <Reveal className="trust-panel__copy">
            <p className="eyebrow eyebrow--light">Clarity is the whole point</p>
            <h2>
              Tax help should feel like <span>light turning on.</span>
            </h2>
            <p>
              Official rules perform the arithmetic. Helpful AI explains the logic
              with verifiable citations. And your sensitive financial data remains
              under your absolute control.
            </p>
            <a className="button button--light" href="#how-it-works">
              Our approach <ArrowUpRight aria-hidden="true" size={16} />
            </a>
          </Reveal>
          <div className="trust-panel__visual" aria-hidden="true">
            <div className="trust-orbit trust-orbit--outer" />
            <div className="trust-orbit trust-orbit--inner" />
            <div className="trust-core">
              <span>
                f<span>.</span>
              </span>
            </div>
            <span className="trust-badge trust-badge--one">
              <BadgeCheck size={17} /> Explainable
            </span>
            <span className="trust-badge trust-badge--two">
              <LockKeyhole size={16} /> Private
            </span>
            <span className="trust-badge trust-badge--three">
              <BookOpenCheck size={17} /> Grounded
            </span>
          </div>
        </div>
      </section>

      {/* 7. Final CTA Banner */}
      <section className="final-cta section-pad">
        <Reveal className="container final-cta__inner">
          <div className="final-cta__spark">
            <Sparkles aria-hidden="true" size={19} />
          </div>
          <p className="eyebrow">Zero filing stress</p>
          <h2>
            Let’s make this
            <br />
            <span>the clear year.</span>
          </h2>
          <p>
            Upload your Form 16 or start the simulator. We’ll calculate the optimal
            regime in seconds.
          </p>
          <MagneticButton
            className="button button--primary"
            onClick={() => navigate('/upload')}
            type="button"
          >
            Upload your documents <ArrowUpRight aria-hidden="true" size={17} />
          </MagneticButton>
        </Reveal>
      </section>
    </>
  )
}
