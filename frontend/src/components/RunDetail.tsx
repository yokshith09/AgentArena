import { useState, type KeyboardEvent, type ReactNode } from 'react'
import FixtureNotice from './FixtureNotice'
import { agents, type DashboardFixture, type FixtureState } from '../mocks/fixtures'
import type { Event, GradeResult, RunDetail as RunRecord } from '../types'

const tabs = ['Timeline', 'Diff', 'Grader', 'Environment'] as const
type RunTab = (typeof tabs)[number]

export default function RunDetailPage({
  fixture,
  fixtureState,
}: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  const requestedRunId = window.location.pathname.split('/').filter(Boolean)[1]
  const run = fixture.runs.find(({ run_id }) => run_id === requestedRunId)
  const [activeTab, setActiveTab] = useState<RunTab>('Timeline')

  if (!run) {
    return (
      <>
        <PageHeading title="Run detail" description="Inspect the trace and evidence for one run." />
        <FixtureNotice fixture={fixture} state={fixtureState} />
        <EmptyState
          title="Run not found in this fixture"
          message="Choose a fixture state with a run to view its detail."
        />
      </>
    )
  }

  const cellRuns = fixture.runs.filter((candidate) =>
    candidate.agent_id === run.agent_id &&
    candidate.task_id === run.task_id &&
    candidate.scenario === run.scenario,
  )
  const runIndex = cellRuns.findIndex(({ run_id }) => run_id === run.run_id)
  const events = fixture.events.filter(({ run_id }) => run_id === run.run_id)

  function selectTab(index: number) {
    const nextTab = tabs[(index + tabs.length) % tabs.length]
    setActiveTab(nextTab)
    document.getElementById(tabId(nextTab))?.focus()
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    if (event.key === 'ArrowRight') {
      event.preventDefault()
      selectTab(index + 1)
    } else if (event.key === 'ArrowLeft') {
      event.preventDefault()
      selectTab(index - 1)
    } else if (event.key === 'Home') {
      event.preventDefault()
      selectTab(0)
    } else if (event.key === 'End') {
      event.preventDefault()
      selectTab(tabs.length - 1)
    }
  }

  return (
    <>
      <PageHeading
        title="Run detail"
        description={run.run_id}
        action={<StatusBadge status={run.status} />}
      />
      <FixtureNotice fixture={fixture} state={fixtureState} />
      {run.error && <div className="notice notice-warning" role="alert">{run.error}</div>}
      {cellRuns.length > 1 && (
        <nav className="run-neighbors" aria-label="Runs in this agent, task, and scenario">
          {runIndex > 0 ? (
            <a className="button button-secondary" href={`/runs/${cellRuns[runIndex - 1].run_id}`}>
              Previous run
            </a>
          ) : <span aria-disabled="true">Previous run</span>}
          <span>Run {run.repeat_index} of {cellRuns.length}</span>
          {runIndex < cellRuns.length - 1 ? (
            <a className="button button-secondary" href={`/runs/${cellRuns[runIndex + 1].run_id}`}>
              Next run
            </a>
          ) : <span aria-disabled="true">Next run</span>}
        </nav>
      )}
      <dl className="summary-grid">
        <SummaryValue
          label="Agent"
          value={agents.find(({ agent_id }) => agent_id === run.agent_id)?.name ?? run.agent_id}
        />
        <SummaryValue label="Task" value={run.task_id} />
        <SummaryValue label="Scenario" value={run.scenario} />
        <SummaryValue label="Model" value={run.model ?? '—'} />
        <SummaryValue label="Tokens in / out" value={`${run.tokens_in ?? '—'} / ${run.tokens_out ?? '—'}`} />
        <SummaryValue label="Cost" value={`${formatMoney(run.cost)} · ${run.cost_confidence ?? 'unknown'}`} />
        <SummaryValue label="Duration" value={run.duration === null ? '—' : `${run.duration.toFixed(1)} s`} />
        <SummaryValue label="Steps / tool calls" value={`${run.steps ?? '—'} / ${run.tool_calls ?? '—'}`} />
        <SummaryValue label="Attempt / repeat" value={`${run.attempt} / ${run.repeat_index}`} />
        <SummaryValue label="Started" value={formatTimestamp(run.started_at)} />
      </dl>
      <div className="tabs" role="tablist" aria-label="Run detail sections">
        {tabs.map((tab, index) => (
          <button
            key={tab}
            id={tabId(tab)}
            type="button"
            role="tab"
            aria-controls="run-detail-panel"
            aria-selected={activeTab === tab}
            tabIndex={activeTab === tab ? 0 : -1}
            onClick={() => setActiveTab(tab)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
          >
            {tab}
          </button>
        ))}
      </div>
      <section
        className="tab-content"
        id="run-detail-panel"
        role="tabpanel"
        tabIndex={0}
        aria-labelledby={tabId(activeTab)}
      >
        <h2>{activeTab}</h2>
        {activeTab === 'Timeline' && <EventTimeline events={events} />}
        {activeTab === 'Diff' && (
          run.workspace_diff
            ? <pre className="code-block">{run.workspace_diff}</pre>
            : <p className="muted-copy">No workspace diff is available for this run.</p>
        )}
        {activeTab === 'Grader' && <GraderPanel result={run.grader_result} />}
        {activeTab === 'Environment' && (
          run.env_fingerprint
            ? <pre className="code-block">{JSON.stringify(run.env_fingerprint, null, 2)}</pre>
            : <p className="muted-copy">No environment fingerprint was recorded for this run.</p>
        )}
      </section>
    </>
  )
}

function EventTimeline({ events }: { events: Event[] }) {
  const [filter, setFilter] = useState('all')
  const orderedEvents = [...events].sort((a, b) =>
    Date.parse(a.ts) - Date.parse(b.ts) || a.id - b.id,
  )
  const eventTypes = [...new Set(orderedEvents.map(({ type }) => type))]
  const visibleEvents = filter === 'all'
    ? orderedEvents
    : orderedEvents.filter(({ type }) => type === filter)
  const faultCalls = new Map<number, number>()

  orderedEvents.forEach((event, index) => {
    if (event.type !== 'fault_injected') return
    const relatedCall = orderedEvents.slice(index + 1).find(({ type }) => type === 'llm_call')
    if (relatedCall) faultCalls.set(event.id, relatedCall.id)
  })

  const relatedCallIds = new Set(faultCalls.values())

  if (!orderedEvents.length) return <p className="muted-copy">No events recorded for this run.</p>

  const firstTimestamp = Date.parse(orderedEvents[0].ts)
  return (
    <>
      <div className="timeline-toolbar">
        <div className="timeline-filters" role="group" aria-label="Filter timeline events">
          <button
            type="button"
            aria-pressed={filter === 'all'}
            onClick={() => setFilter('all')}
          >
            All events
          </button>
          {eventTypes.map((type) => (
            <button
              key={type}
              type="button"
              aria-pressed={filter === type}
              onClick={() => setFilter(type)}
            >
              {type}
            </button>
          ))}
        </div>
        <span className="timeline-count" role="status">
          Showing {visibleEvents.length} of {orderedEvents.length} events
        </span>
      </div>
      <ol className="event-list">
        {visibleEvents.map((event) => {
          const faultCallId = faultCalls.get(event.id)
          const followsFault = relatedCallIds.has(event.id)
          return (
            <li
              key={event.id}
              id={`event-${event.id}`}
              className={[
                event.type === 'fault_injected' ? 'event-fault' : '',
                followsFault ? 'event-related-to-fault' : '',
              ].filter(Boolean).join(' ')}
            >
              <div className="event-topline">
                <span className="event-type">{event.type}</span>
                <time dateTime={event.ts}>+{relativeSeconds(firstTimestamp, event.ts)}s</time>
              </div>
              <p>{event.error ?? eventSummary(event)}</p>
              <div className="event-meta">
                {event.agent_role && <span>Role: {event.agent_role}</span>}
                {event.latency !== null && <span>Latency: {event.latency.toLocaleString()} ms</span>}
                {followsFault && <span>Following an injected fault</span>}
              </div>
              {faultCallId !== undefined && (
                <a className="event-related-link" href={`#event-${faultCallId}`}>
                  Associated LLM call
                </a>
              )}
              <details>
                <summary>Event payload</summary>
                <pre className="code-block">{JSON.stringify(event.payload, null, 2)}</pre>
                {event.payload.truncated === true && <p>Payload is truncated.</p>}
              </details>
            </li>
          )
        })}
      </ol>
    </>
  )
}

function GraderPanel({ result }: { result: GradeResult | null }) {
  if (!result) return <p className="muted-copy">No grader result was recorded for this run.</p>
  return (
    <div className="grader-result">
      <div className="grader-summary">
        <StatusBadge status={result.passed ? 'PASS' : 'FAIL'} />
        <p>{result.summary}</p>
        <p>{result.tamper_detected ? 'Protected files were modified.' : 'No protected-file tampering detected.'}</p>
        {result.error && <p role="alert">{result.error}</p>}
      </div>
      {result.suites.length > 0 && (
        <div className="table-scroll">
          <table>
            <caption>Grader test suites</caption>
            <thead>
              <tr>
                <th scope="col">Suite</th>
                <th scope="col">Result</th>
                <th className="num" scope="col">Passed</th>
                <th className="num" scope="col">Failed</th>
                <th className="num" scope="col">Total</th>
              </tr>
            </thead>
            <tbody>
              {result.suites.map((suite) => (
                <tr key={suite.name}>
                  <th scope="row">{suite.name}</th>
                  <td>{suite.passed ? 'Pass' : 'Fail'}</td>
                  <td className="num">{suite.tests_total - suite.tests_failed}</td>
                  <td className="num">{suite.tests_failed}</td>
                  <td className="num">{suite.tests_total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function PageHeading({
  title,
  description,
  action,
}: {
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  )
}

function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <section className="empty-state" role="status">
      <h2>{title}</h2>
      <p>{message}</p>
    </section>
  )
}

function SummaryValue({ label, value }: { label: string; value: string }) {
  return <div className="summary-value"><dt>{label}</dt><dd>{value}</dd></div>
}

function StatusBadge({ status }: { status: RunRecord['status'] }) {
  const tone = status === 'PASS' ? 'positive' :
    status === 'FAIL' ? 'negative' :
      status === 'INFRA_ERROR' ? 'warning' : 'neutral'
  return <span className={`status-pill status-${tone}`}>{status ?? 'Pending'}</span>
}

function eventSummary(event: Event) {
  const toolName = event.payload.name
  const statusCode = event.payload.status_code
  if (typeof toolName === 'string') return `Requested ${toolName}.`
  if (typeof statusCode === 'number') return `HTTP ${statusCode}.`
  const faultId = event.payload.fault_id
  if (typeof faultId === 'string') return `Injected ${faultId}.`
  return `Run event recorded${event.agent_role ? ` for ${event.agent_role}` : ''}.`
}

function relativeSeconds(start: number, timestamp: string) {
  const current = Date.parse(timestamp)
  if (!Number.isFinite(start) || !Number.isFinite(current)) return '—'
  return Math.max(0, Math.round((current - start) / 1000)).toString()
}

function formatMoney(value: number | null) {
  return value === null ? '—' : `$${value.toFixed(4)}`
}

function formatTimestamp(value: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function tabId(tab: RunTab) {
  return `run-tab-${tab.toLowerCase()}`
}
