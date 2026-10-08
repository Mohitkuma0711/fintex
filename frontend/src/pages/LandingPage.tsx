import { lazy, Suspense, useEffect, useState } from 'react'
import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  BookOpenCheck,
  FileCheck2,
  Fingerprint,
  LockKeyhole,
  Sparkles,
  WalletCards,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { MagneticButton } from '../components/motion/MagneticButton'
import { Reveal } from '../components/motion/Reveal'
import { Stagger, StaggerItem } from '../components/motion/Stagger'

const TaxScene = lazy(async () => {
  const { TaxScene: Scene } = await import('../components/hero/TaxScene')
  return { default: Scene }
})

const steps = [
  {
    number: '01',
    title: 'Upload',
    description:
      'Bring your tax documents together in one private, organized place.',
    icon: WalletCards,
  },
  {
    number: '02',
    title: 'Understand',
    description:
      'Review extracted details and see where every piece of information came from.',
    icon: FileCheck2,
  },
  {
    number: '03',
    title: 'Optimize',
    description:
      'Explore clear, explainable next steps grounded in the rules that apply to you.',
    icon: Sparkles,
  },
]

const features = [
  {
    title: 'Every number, explained',
    description:
      'Follow a clear calculation trail and understand the rules behind each result.',
    icon: BadgeCheck,
    tone: 'blue',
  },
  {
    title: 'Guidance with sources',
    description:
      'Explore answers connected to official sources, not confident-sounding guesses.',
    icon: BookOpenCheck,
    tone: 'green',
  },
  {
    title: 'Your data stays yours',
    description:
      'A privacy-first experience built around sensitive financial information.',
    icon: Fingerprint,
    tone: 'amber',
  },
]

interface NavigatorWithDeviceMemory extends Navigator {
  deviceMemory?: number
}

function canRenderScene() {
  const device = navigator as NavigatorWithDeviceMemory
  const lowMemory = device.deviceMemory !== undefined && device.deviceMemory <= 4
  const lowCpu = navigator.hardwareConcurrency > 0 && navigator.hardwareConcurrency <= 4
  const smallScreen = window.matchMedia('(max-width: 760px)').matches
  return !lowMemory && !lowCpu && !smallScreen
}

function HeroArtwork() {
  const [reducedMotion, setReducedMotion] = useState(() =>
    window.matchMedia('(prefers-reduced-motion: reduce)').matches,
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
    const timeoutId = window.setTimeout(() => setSceneReady(true), 2200)
    return () => window.clearTimeout(timeoutId)
  }, [showScene])

  return (
    <div className="hero-art" aria-label="A visual preview of your FinTax workspace">
      <div className="hero-art__glow" aria-hidden="true" />
      {showScene && sceneReady ? (
        <>
          <Suspense fallback={<div className="scene-fallback" aria-hidden="true" />}>
            <div className="hero-art__canvas">
              <TaxScene />
            </div>
          </Suspense>
          <span className="scene-currency" aria-hidden="true">₹</span>
        </>
      ) : (
        <div className="scene-fallback" aria-hidden="true">
          <span className="scene-fallback__coin">₹</span>
          <span className="scene-fallback__document" />
          <span className="scene-fallback__chart" />
        </div>
      )}

      <div className="workspace-card">
        <div className="workspace-card__top">
          <div>
            <span className="workspace-card__eyebrow">TAX WORKSPACE PREVIEW</span>
            <h2>Everything, in one place.</h2>
          </div>
          <span className="workspace-card__status">
            <span /> Preview
          </span>
        </div>
        <div className="workspace-card__files">
          <div className="file-row">
            <span className="file-row__icon file-row__icon--blue">
              <FileCheck2 aria-hidden="true" size={18} />
            </span>
            <span className="file-row__details">
              <strong>Form 16</strong>
              <small>Example document</small>
            </span>
            <BadgeCheck className="file-row__check" aria-hidden="true" size={18} />
          </div>
          <div className="file-row">
            <span className="file-row__icon file-row__icon--green">
              <WalletCards aria-hidden="true" size={18} />
            </span>
            <span className="file-row__details">
              <strong>Investment summary</strong>
              <small>Example document</small>
            </span>
            <ArrowUpRight className="file-row__arrow" aria-hidden="true" size={17} />
          </div>
        </div>
        <div className="workspace-card__foot">
          <span><LockKeyhole aria-hidden="true" size={13} /> Private by design</span>
          <span>Illustrative only</span>
        </div>
      </div>

      <div className="float-note float-note--source">
        <span className="float-note__icon"><BookOpenCheck aria-hidden="true" size={16} /></span>
        <span><strong>Clear sources</strong><small>Know where it comes from</small></span>
      </div>
      <div className="float-note float-note--trace">
        <span className="float-note__icon float-note__icon--green"><BadgeCheck aria-hidden="true" size={16} /></span>
        <span><strong>Made to make sense</strong><small>Every step, explained</small></span>
      </div>
    </div>
  )
}

export function LandingPage() {
  const navigate = useNavigate()

  return (
    <>
      <section className="hero-section">
        <div className="hero-container">
          <div className="hero-copy">
            <Reveal>
              <p className="eyebrow"><span className="eyebrow__spark" /> A clearer way to do taxes</p>
              <h1>
                Your taxes,
                <br />
                <span className="headline-accent">without the</span>
                <br />
                <span className="headline-serif">guesswork.</span>
              </h1>
              <p className="hero-copy__description">
                A calmer, clearer way to understand your taxes. See what matters,
                why it matters, and what you can do next.
              </p>
              <div className="hero-copy__actions">
                <MagneticButton
                  className="button button--primary"
                  onClick={() => navigate('/onboarding')}
                  type="button"
                >
                  Start your journey <ArrowUpRight aria-hidden="true" size={17} />
                </MagneticButton>
                <a className="text-link" href="#how-it-works">
                  See how it works <ArrowDown aria-hidden="true" size={15} />
                </a>
              </div>
              <div className="hero-trust">
                <span><LockKeyhole aria-hidden="true" size={14} /> Private by design</span>
                <span className="hero-trust__divider" aria-hidden="true" />
                <span>Built for India</span>
              </div>
            </Reveal>
          </div>
          <HeroArtwork />
        </div>
        <div className="hero-bottom container">
          <span className="hero-bottom__label">LESS PAPERWORK. MORE PEACE OF MIND.</span>
          <a href="#how-it-works">Scroll to explore <ArrowDown aria-hidden="true" size={14} /></a>
        </div>
      </section>

      <section className="journey-section section-pad" id="how-it-works">
        <div className="container">
          <Reveal className="section-heading">
            <p className="eyebrow">A better kind of tax season</p>
            <h2>Three steps to <span>feeling in control.</span></h2>
            <p>From a pile of paperwork to a plan that finally makes sense.</p>
          </Reveal>
          <div className="journey-grid">
            {steps.map(({ number, title, description, icon: Icon }, index) => (
              <Reveal className={`journey-step journey-step--${index + 1}`} delay={index * 0.1} key={number}>
                <div className="journey-step__top">
                  <span className="journey-step__number">{number}</span>
                  <span className="journey-step__icon"><Icon aria-hidden="true" size={21} /></span>
                </div>
                <h3>{title}</h3>
                <p>{description}</p>
                {index < steps.length - 1 && <span className="journey-step__connector" aria-hidden="true" />}
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="features-section section-pad" id="features">
        <div className="container">
          <Reveal className="features-intro">
            <div>
              <p className="eyebrow">Confidence, built in</p>
              <h2>Not just answers.<br /><span>Answers you can trust.</span></h2>
            </div>
            <p>Good financial decisions start with clarity. We make the details easier to understand, without hiding what matters.</p>
          </Reveal>
          <Stagger className="feature-grid">
            {features.map(({ title, description, icon: Icon, tone }) => (
              <StaggerItem className="feature-card" key={title}>
                <span className={`feature-card__icon feature-card__icon--${tone}`}>
                  <Icon aria-hidden="true" size={22} />
                </span>
                <h3>{title}</h3>
                <p>{description}</p>
                <span className="feature-card__arrow" aria-hidden="true"><ArrowRight size={17} /></span>
              </StaggerItem>
            ))}
          </Stagger>
        </div>
      </section>

      <section className="trust-section section-pad" id="trust">
        <div className="container trust-panel">
          <Reveal className="trust-panel__copy">
            <p className="eyebrow eyebrow--light">Clarity is the whole point</p>
            <h2>Tax help should feel like <span>light turning on.</span></h2>
            <p>Real rules do the calculating. Helpful AI makes the explanations easier to follow. And you stay in control at every step.</p>
            <a className="button button--light" href="/#how-it-works">
              Our approach <ArrowUpRight aria-hidden="true" size={16} />
            </a>
          </Reveal>
          <div className="trust-panel__visual" aria-hidden="true">
            <div className="trust-orbit trust-orbit--outer" />
            <div className="trust-orbit trust-orbit--inner" />
            <div className="trust-core"><span>f<span>.</span></span></div>
            <span className="trust-badge trust-badge--one"><BadgeCheck size={17} /> Explainable</span>
            <span className="trust-badge trust-badge--two"><LockKeyhole size={16} /> Private</span>
            <span className="trust-badge trust-badge--three"><BookOpenCheck size={17} /> Grounded</span>
          </div>
        </div>
      </section>

      <section className="final-cta section-pad">
        <Reveal className="container final-cta__inner">
          <div className="final-cta__spark"><Sparkles aria-hidden="true" size={19} /></div>
          <p className="eyebrow">A little less tax stress</p>
          <h2>Let’s make this<br /><span>the clear year.</span></h2>
          <p>Start with what you have. We’ll help you make sense of the rest.</p>
          <button
            className="button button--primary"
            onClick={() => navigate('/onboarding')}
            type="button"
          >
            Get started <ArrowUpRight aria-hidden="true" size={17} />
          </button>
        </Reveal>
      </section>
    </>
  )
}
