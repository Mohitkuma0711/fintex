import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { ArrowUp, BookOpenText, MessageCircle, Plus, ShieldCheck } from 'lucide-react'
import { EmptyState } from '../components/ui/EmptyState'
import { Skeleton } from '../components/ui/Skeleton'
import {
  ApiError,
  fintaxApi,
  streamChatMessage,
  type ChatCitation,
  type ChatMessage,
} from '../lib/api'
import { formatINRExact } from '../lib/formatters'

const suggestedQuestions = [
  'Show my verified tax-saving opportunities and estimated savings.',
  'Why is the new regime better for me?',
  'Can you explain a step in my latest calculation?',
  'What if I contribute more to NPS?',
]

function CitationChips({ citations, content }: { citations: ChatCitation[]; content: string }) {
  if (citations.length === 0) {
    const isGreeting = /^(hi|hello|hey|hiya|good morning|good afternoon|good evening)[!.]?/i.test(content.trim())
    if (isGreeting) return null
    return <p className="chat-no-citation">No official source was retrieved; this answer is intentionally unsure.</p>
  }
  return (
    <ul aria-label="Official sources" className="chat-citations">
      {citations.map((citation, index) => (
        <li key={`${citation.link}-${citation.section}-${index}`}>
          <a href={citation.link} rel="noreferrer" target="_blank" title={`${citation.source} — ${citation.section}`}>
            <BookOpenText aria-hidden="true" size={14} />
            <span>{citation.source} · {citation.section}</span>
          </a>
        </li>
      ))}
    </ul>
  )
}

function MessageBubble({ message, isThinking }: { message: ChatMessage; isThinking?: boolean }) {
  const isAssistant = message.role === 'assistant'
  const reducedMotion = useReducedMotion()
  return (
    <motion.article
      animate={{ opacity: 1, y: 0 }}
      aria-label={isAssistant ? 'CA Advisor response' : 'Your message'}
      className={`chat-message${isAssistant ? ' chat-message--assistant' : ' chat-message--user'}`}
      initial={{ opacity: 0, y: 8 }}
      transition={{ duration: reducedMotion ? 0 : 0.22 }}
    >
      <div className="chat-message__identity">
        <span aria-hidden="true">{isAssistant ? <ShieldCheck size={15} /> : 'You'}</span>
        <strong>{isAssistant ? 'CA Advisor' : 'You'}</strong>
      </div>
      <div className="chat-message__content">
        {message.content ? <p>{message.content}</p> : isThinking ? (
          <span aria-label="CA Advisor is thinking" className="chat-typing" role="status">
            <i /><i /><i />
          </span>
        ) : null}
      </div>
      {isAssistant && message.content && <CitationChips citations={message.citations} content={message.content} />}
    </motion.article>
  )
}

function ContextPanel() {
  const profileQuery = useQuery({
    queryKey: ['user-profile'],
    queryFn: fintaxApi.getProfile,
  })
  const profile = profileQuery.data?.confirmed_profile
  if (profileQuery.isPending) {
    return (
      <aside aria-label="Loading your tax context" className="chat-context">
        <Skeleton className="chat-context__skeleton" />
      </aside>
    )
  }
  if (profileQuery.isError) {
    return (
      <aside aria-label="Tax context" className="chat-context">
        <h2>Your context</h2>
        <p role="alert">{profileQuery.error.message}</p>
      </aside>
    )
  }
  if (!profile) {
    return (
      <aside aria-label="Tax context" className="chat-context">
        <h2>Your context</h2>
        <p>Your confirmed profile is not available. Chat will not infer personal figures.</p>
      </aside>
    )
  }

  const amounts: [string, string][] = [
    ['Basic salary', profile.salary_components.basic_salary],
    ['Dearness allowance', profile.salary_components.dearness_allowance],
    ['HRA received', profile.salary_components.hra_received],
    ['Other allowances', profile.salary_components.other_allowances],
    ['Other income', profile.other_income],
    ['Rent paid', profile.hra_inputs.rent_paid],
    ['80C claimed', profile.deductions_claimed.section_80c],
    ['80D claimed', profile.deductions_claimed.section_80d],
    ['80CCD(1B) claimed', profile.deductions_claimed.section_80ccd_1b],
    ['80E claimed', profile.deductions_claimed.section_80e],
    ['24(b) claimed', profile.deductions_claimed.section_24b],
  ]
  return (
    <aside aria-label="Confirmed profile context" className="chat-context">
      <p className="eyebrow">PRIVATE CONTEXT</p>
      <h2>Your confirmed inputs</h2>
      <p className="chat-context__note">
        FY {profile.financial_year} · {profile.employment_type === 'employee' ? 'Employee' : 'Business / freelancer'}
      </p>
      <dl>
        {amounts.map(([label, value]) => (
          <div key={label}><dt>{label}</dt><dd>{formatINRExact(value)}</dd></div>
        ))}
      </dl>
      <p className="chat-context__note">Input values only; tax results come from the deterministic engine.</p>
    </aside>
  )
}

export function ChatPage() {
  const queryClient = useQueryClient()
  const reducedMotion = useReducedMotion()
  const sessionsQuery = useQuery({
    queryKey: ['chat-sessions'],
    queryFn: fintaxApi.listChatSessions,
  })
  const [sessionId, setSessionId] = useState<string | null | undefined>(undefined)
  const activeSessionId = sessionId === undefined
    ? sessionsQuery.data?.[0]?.id ?? null
    : sessionId
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const [streamingCitations, setStreamingCitations] = useState<ChatCitation[]>([])
  const streamingRef = useRef(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const historyQuery = useQuery({
    queryKey: ['chat-history', activeSessionId],
    queryFn: () => fintaxApi.getChatHistory(activeSessionId!),
    enabled: activeSessionId !== null,
  })

  useEffect(() => {
    if (!streamingRef.current && historyQuery.data) {
      setMessages(historyQuery.data.messages)
    }
  }, [historyQuery.data])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth' })
  }, [messages, streamingText, sending, reducedMotion])

  async function sendMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const question = input.trim()
    if (!question || sending) return
    setSending(true)
    setStreamingText('')
    setStreamingCitations([])
    streamingRef.current = true
    setInput('')
    let activeId = activeSessionId
    try {
      if (!activeId) {
        const session = await fintaxApi.createChatSession(question.slice(0, 200))
        activeId = session.id
        setSessionId(session.id)
        await queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      }
      const optimisticUserMessage: ChatMessage = {
        id: `local-user-${Date.now()}`,
        role: 'user',
        content: question,
        citations: [],
        created_at: new Date().toISOString(),
      }
      setMessages((current) => [...current, optimisticUserMessage])
      let completed = false
      let failureText: string | null = null
      await streamChatMessage(activeId, question, (streamEvent) => {
        if (streamEvent.type === 'delta') {
          setStreamingText((current) => current + streamEvent.text)
        } else if (streamEvent.type === 'citations') {
          setStreamingCitations(streamEvent.citations)
        } else if (streamEvent.type === 'done') {
          completed = true
        } else if (streamEvent.type === 'error') {
          failureText = streamEvent.message
        }
      })
      if (completed) {
        const history = await fintaxApi.getChatHistory(activeId)
        setMessages(history.messages)
        await queryClient.invalidateQueries({ queryKey: ['chat-sessions'] })
      } else if (failureText) {
        const errorMessage = failureText
        setMessages((current) => [...current, {
          id: `local-assistant-${Date.now()}`,
          role: 'assistant',
          content: errorMessage,
          citations: [],
          created_at: new Date().toISOString(),
        }])
      }
    } catch (error) {
      const message = error instanceof ApiError || error instanceof Error
        ? error.message
        : 'The assistant could not complete this request.'
      setMessages((current) => [...current, {
        id: `local-assistant-${Date.now()}`,
        role: 'assistant',
        content: message,
        citations: [],
        created_at: new Date().toISOString(),
      }])
    } finally {
      streamingRef.current = false
      setSending(false)
      setStreamingText('')
      setStreamingCitations([])
      if (activeId) {
        await queryClient.invalidateQueries({ queryKey: ['chat-history', activeId] })
      }
    }
  }

  function startNewConversation() {
    setSessionId(null)
    setMessages([])
    setInput('')
  }

  if (sessionsQuery.isPending) {
    return (
      <section aria-label="Loading chat" className="chat-page container">
        <Skeleton className="dashboard-skeleton dashboard-skeleton--heading" />
        <Skeleton className="chat-page__loading" />
      </section>
    )
  }

  if (sessionsQuery.isError) {
    return (
      <section className="chat-page container">
        <EmptyState
          icon={<MessageCircle aria-hidden="true" size={26} />}
          title="Your conversations could not be loaded."
          description={sessionsQuery.error.message}
          action={<button className="button" onClick={() => void sessionsQuery.refetch()} type="button">Try again</button>}
        />
      </section>
    )
  }

  const liveAssistant: ChatMessage | null = sending
    ? {
        id: 'live-assistant',
        role: 'assistant',
        content: streamingText,
        citations: streamingCitations,
        created_at: new Date().toISOString(),
      }
    : null

  return (
    <section className="chat-page container">
      <header className="chat-heading">
        <div>
          <p className="eyebrow">EXPLAIN · OFFICIAL SOURCES</p>
          <h1>Good questions. <span>Grounded answers.</span></h1>
          <p>CA Advisor uses official references and your saved calculation tools. If evidence is missing, it will say so.</p>
        </div>
        <button className="button chat-new-button" onClick={startNewConversation} type="button">
          <Plus aria-hidden="true" size={16} /> New conversation
        </button>
      </header>

      <div className="chat-layout">
        <main aria-label="Tax assistant conversation" className="chat-main">
          <div className="chat-toolbar">
            <label>
              <span>Conversation history</span>
              <select
                onChange={(event) => {
                  setSessionId(event.currentTarget.value || null)
                  setMessages([])
                }}
                value={activeSessionId ?? ''}
              >
                <option value="">New conversation</option>
                {sessionsQuery.data.map((session) => (
                  <option key={session.id} value={session.id}>
                    {session.title || 'Tax conversation'}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {historyQuery.isError && (
            <p className="chat-error" role="alert">{historyQuery.error.message}</p>
          )}
          <div aria-live="polite" className="chat-transcript">
            {messages.length === 0 && !sending && (
              <section className="chat-welcome">
                <span aria-hidden="true" className="chat-welcome__icon"><MessageCircle size={22} /></span>
                <h2>What would you like explained?</h2>
                <p>Ask about a calculation or an Indian income-tax topic. Relevant answers include official citations.</p>
                <div className="chat-suggestions" aria-label="Suggested questions">
                  {suggestedQuestions.map((question) => (
                    <button key={question} onClick={() => setInput(question)} type="button">{question}</button>
                  ))}
                </div>
              </section>
            )}
            {messages.map((message) => <MessageBubble key={message.id} message={message} />)}
            <AnimatePresence initial={false}>
              {liveAssistant && (
                <MessageBubble
                  isThinking={sending && !streamingText}
                  key={liveAssistant.id}
                  message={liveAssistant}
                />
              )}
            </AnimatePresence>
            <div ref={bottomRef} />
          </div>

          <form className="chat-composer" onSubmit={(event) => void sendMessage(event)}>
            <label className="sr-only" htmlFor="chat-message">Ask a tax question</label>
            <textarea
              disabled={sending}
              id="chat-message"
              maxLength={4000}
              onChange={(event) => setInput(event.currentTarget.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  event.currentTarget.form?.requestSubmit()
                }
              }}
              placeholder="Ask about a tax rule or your calculation…"
              ref={inputRef}
              rows={2}
              value={input}
            />
            <button aria-label="Send question" className="chat-send-button" disabled={sending || !input.trim()} type="submit">
              {sending ? <span className="chat-send-spinner" aria-hidden="true" /> : <ArrowUp aria-hidden="true" size={18} />}
            </button>
            <small>Enter to send · Shift + Enter for a new line</small>
          </form>
        </main>
        <ContextPanel />
      </div>
      <p className="chat-disclaimer">CA Advisor provides guidance, not professional tax advice. It will not guarantee legal outcomes or investment returns.</p>
    </section>
  )
}
