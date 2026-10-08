import { ArrowLeft, ArrowUpRight, FileQuestion, LockKeyhole } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState } from '../components/ui/EmptyState'

const pages = {
  onboarding: {
    title: 'A good place to begin.',
    description: 'A few simple steps will help us make your tax workspace feel like yours.',
    action: 'Continue',
    to: '/upload',
  },
  upload: {
    title: 'Bring your documents together.',
    description: 'Your private document workspace is being prepared. Upload flows are coming soon.',
    action: 'Back to overview',
    to: '/',
  },
  review: {
    title: 'Your details, clearly laid out.',
    description: 'When documents are ready, you’ll be able to review every extracted detail here.',
    action: 'Explore how it works',
    to: '/#how-it-works',
  },
  dashboard: {
    title: 'Your financial picture, in one place.',
    description: 'Your dashboard will bring together verified details, explanations, and next steps.',
    action: 'Start with your documents',
    to: '/upload',
  },
  simulator: {
    title: 'Explore your options.',
    description: 'Compare scenarios with a transparent, rules-based simulator. It is not available yet.',
    action: 'Back to overview',
    to: '/',
  },
  chat: {
    title: 'Good questions deserve grounded answers.',
    description: 'When chat is available, tax guidance will include links to official sources.',
    action: 'See our approach',
    to: '/#trust',
  },
  report: {
    title: 'Your report will live here.',
    description: 'Reports will include a readable calculation trail and plain-language explanations.',
    action: 'Explore the journey',
    to: '/#how-it-works',
  },
  'not-found': {
    title: 'This page isn’t here.',
    description: 'The link may have moved. You can head back to the FinTax AI home page.',
    action: 'Go home',
    to: '/',
  },
}

type PlaceholderPageKey = keyof typeof pages

export function PlaceholderPage({ page }: { page: PlaceholderPageKey }) {
  const content = pages[page]

  return (
    <section className="placeholder-page container">
      <div className="placeholder-page__topline">
        <Link className="text-link" to="/">
          <ArrowLeft aria-hidden="true" size={15} /> FinTax AI home
        </Link>
        <span><LockKeyhole aria-hidden="true" size={14} /> Private by design</span>
      </div>
      <EmptyState
        icon={<FileQuestion aria-hidden="true" size={28} />}
        title={content.title}
        description={content.description}
        action={
          <Link className="button button--primary" to={content.to}>
            {content.action} <ArrowUpRight aria-hidden="true" size={16} />
          </Link>
        }
      />
    </section>
  )
}
