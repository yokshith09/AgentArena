import { useState, type FormEvent, type ReactNode } from 'react'
import {
  agents,
  mockFixtures,
  scenarios,
  tasks,
  type DashboardFixture,
  type FixtureState,
} from './mocks/fixtures'
import type { Benchmark, Event, ResilienceRow, ResultRow, RunDetail } from './types'
import './App.css'

const stateOptions: Array<{ value: FixtureState; label: string }> = [
  { value: 'success', label: 'Completed' },
  { value: 'empty', label: 'Empty' },
  { value: 'infra', label: 'INFRA excluded' },
  { value: 'fault', label: 'Fault injected' },
  { value: 'partial', label: 'In progress' },
  { value: 'halted', label: 'Spend cap halted' },
]

const navigation = [
  { label: 'Leaderboard', href: '/' },
  { label: 'Benchmarks', href: '/benchmarks' },
  { label: 'Compare', href: '/compare' },
  { label: 'Failure scenarios', href: '/resilience' },
  { label: 'Catalog', href: '/catalog' },
  { label: 'Limitations', href: '/limitations' },
]

type Route =
  | 'leaderboard'
  | 'benchmarks'
  | 'new-benchmark'
  | 'compare'
  | 'run-detail'
  | 'run-list'
  | 'resilience'
  | 'catalog'
  | 'security'
  | 'limitations'

function getRoute(path: string): Route {
  if (path === '/benchmarks/new') return 'new-benchmark'
  if (path === '/benchmarks') return 'benchmarks'
  if (path === '/compare') return 'compare'
  if (path.startsWith('/runs/')) return 'run-detail'
  if (path === '/runs') return 'run-list'
  if (path === '/resilience') return 'resilience'
  if (path === '/catalog') return 'catalog'
  if (path === '/security') return 'security'
  if (path === '/limitations') return 'limitations'
  return 'leaderboard'
}

function withQuery(changes: Record<string, string | null>) {
  const params = new URLSearchParams(window.location.search)
  Object.entries(changes).forEach(([key, value]) => {
    if (value) params.set(key, value)
    else params.delete(key)
  })
  const query = params.toString()
  return `${window.location.pathname}${query ? `?${query}` : ''}`
}

function App() {
  const route = getRoute(window.location.pathname)
  const params = new URLSearchParams(window.location.search)
  const requestedState = params.get('state')
  const fixtureState = stateOptions.some(({ value }) => value === requestedState)
    ? requestedState as FixtureState
    : 'success'
  const fixture = mockFixtures[fixtureState]
  const liveMode = params.get('mode') === 'live'
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="app-frame">
      <header className="app-header">
        <a className="brand" href="/" aria-label="AgentArena home">
          <span className="brand-mark" aria-hidden="true">A</span>
          <span>AgentArena</span>
        </a>
        <button
          className="menu-toggle"
          type="button"
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? 'Close menu' : 'Menu'}
        </button>
        <nav
          id="primary-navigation"
          className={`primary-navigation${menuOpen ? ' is-open' : ''}`}
          aria-label="Primary navigation"
        >
          {navigation.map((item) => (
            <a
              key={item.href}
              href={item.href}
              aria-current={item.href === '/' ? route === 'leaderboard' ? 'page' : undefined :
                window.location.pathname === item.href ? 'page' : undefined}
              onClick={() => setMenuOpen(false)}
            >
              {item.label}
            </a>
          ))}
        </nav>
        <div className="header-controls">
          {['leaderboard', 'compare', 'resilience'].includes(route) && (
            <label className="select-control benchmark-select">
              <span>Benchmark</span>
              <select
                aria-label="Select benchmark"
                value={fixture.benchmark?.benchmark_id ?? ''}
                disabled={!fixture.benchmark}
                onChange={(event) => {
                  window.location.href = withQuery({ benchmark: event.target.value })
                }}
              >
                {fixture.benchmark ? (
                  <option value={fixture.benchmark.benchmark_id}>{fixture.benchmark.name}</option>
                ) : (
                  <option value="">No benchmark selected</option>
                )}
              </select>
            </label>
          )}
          <label className="select-control fixture-select">
            <span>Fixture state</span>
            <select
              aria-label="Select mock fixture state"
              value={fixtureState}
              onChange={(event) => {
                window.location.href = withQuery({ state: event.target.value })
              }}
            >
              {stateOptions.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </label>
          <a
            className={`mode-switch${liveMode ? ' is-live' : ''}`}
            href={withQuery({ mode: liveMode ? null : 'live' })}
          >
            {liveMode ? 'Live mode' : 'Mock mode'}
          </a>
        </div>
      </header>

      <div className="workspace">
        <div className="mock-ribbon" role="status">
          {liveMode ? 'LIVE API NOT CONNECTED' : 'MOCK DATA — illustrative fixtures, not benchmark results'}
        </div>
        <main id="main-content" className="main-sheet">
          {liveMode ? (
            <LiveUnavailable />
          ) : (
            <RouteView
              route={route}
              fixture={fixture}
              fixtureState={fixtureState}
            />
          )}
        </main>
      </div>
      <footer className="app-footer">
        <span>AgentArena</span>
        <span>Every metric links back to the runs behind it.</span>
      </footer>
    </div>
  )
}

function RouteView({
  route,
  fixture,
  fixtureState,
}: {
  route: Route
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  switch (route) {
    case 'leaderboard':
      return <Leaderboard fixture={fixture} fixtureState={fixtureState} />
    case 'benchmarks':
      return <Benchmarks benchmark={fixture.benchmark} />
    case 'new-benchmark':
      return <NewBenchmark />
    case 'compare':
      return <Compare fixture={fixture} />
    case 'run-detail':
      return <RunDetailPage fixture={fixture} />
    case 'run-list':
      return <RunList fixture={fixture} />
    case 'resilience':
      return <Resilience fixture={fixture} fixtureState={fixtureState} />
    case 'catalog':
      return <Catalog />
    case 'security':
      return <Security />
    case 'limitations':
      return <Limitations />
  }
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

function FixtureNotice({ fixture, state }: { fixture: DashboardFixture; state: FixtureState }) {
  if (state === 'partial' && fixture.benchmark) {
    return (
      <div className="notice notice-info" role="status">
        Results incomplete ({fixture.benchmark.progress.done} of {fixture.benchmark.progress.total} runs).
        Counts reflect the runs available so far.
      </div>
    )
  }
  if (state === 'halted' && fixture.benchmark) {
    return (
      <div className="notice notice-warning" role="alert">
        Stopped at spend cap ${fixture.benchmark.config.spend_cap_usd.toFixed(2)}.
        No additional runs were scheduled.
      </div>
    )
  }
  if (state === 'infra') {
    return (
      <div className="notice notice-warning" role="status">
        INFRA_ERROR runs are excluded from statistics. The exclusion count is shown in each result row.
      </div>
    )
  }
  if (state === 'fault') {
    return (
      <div className="notice notice-info" role="status">
        Fault scenario: provider_503_outage. Injected failures remain visible in the run trace.
      </div>
    )
  }
  return null
}

function Leaderboard({
  fixture,
  fixtureState,
}: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  const [selected, setSelected] = useState<string[]>([])
  return (
    <>
      <PageHeading
        title="Leaderboard"
        description={fixture.benchmark?.name ?? 'Agent performance across the selected benchmark.'}
        action={<StateBadge state={fixture.benchmark?.state ?? 'No benchmark'} />}
      />
      <FixtureNotice fixture={fixture} state={fixtureState} />
      {fixture.results.length === 0 ? (
        <EmptyState
          title="No benchmark results yet"
          message="Launch a benchmark to compare agents on the same tasks."
          action={<a className="button button-primary" href="/benchmarks/new">Launch a benchmark</a>}
        />
      ) : (
        <>
          <div className="section-toolbar">
            <div className="scenario-control">
              <label htmlFor="scenario">Scenario</label>
              <select id="scenario" defaultValue={fixture.results[0].scenario}>
                {scenarios.map((scenario) => (
                  <option key={scenario.id} value={scenario.id}>{scenario.id}</option>
                ))}
              </select>
            </div>
            <span>{fixture.results.length} agents · generated Jan 1, 2026</span>
          </div>
          {selected.length > 1 && (
            <a className="button button-secondary compare-action" href="/compare">
              Compare {selected.length} agents
            </a>
          )}
          <div className="table-scroll leaderboard-table-region" role="region" aria-label="Leaderboard results" tabIndex={0}>
            <table className="leaderboard-table">
              <thead>
                <tr>
                  <th scope="col"><span className="sr-only">Select</span></th>
                  <th scope="col">Agent</th>
                  <th className="num" scope="col">Success rate</th>
                  <th className="num" scope="col">Cost (USD)</th>
                  <th className="num" scope="col">Steps (LLM calls)</th>
                  <th className="num" scope="col">Tool calls requested</th>
                  <th className="num" scope="col">Time (s)</th>
                  <th className="num" scope="col">INFRA excluded</th>
                </tr>
              </thead>
              <tbody>
                {fixture.results.map((result) => (
                  <LeaderboardRow
                    key={result.agent_id}
                    result={result}
                    selected={selected.includes(result.agent_id)}
                    onSelect={(checked) => setSelected((current) =>
                      checked
                        ? [...current, result.agent_id]
                        : current.filter((id) => id !== result.agent_id),
                    )}
                  />
                ))}
              </tbody>
            </table>
          </div>
          <div className="mobile-leaderboard" aria-label="Leaderboard results">
            {fixture.results.map((result, index) => {
              const agent = agents.find(({ agent_id }) => agent_id === result.agent_id)
              return (
                <article className="agent-summary" key={result.agent_id}>
                  <div className="agent-summary-heading">
                    <label className="agent-summary-select">
                      <input
                        aria-label={`Select ${agent?.name ?? result.agent_id} for comparison`}
                        type="checkbox"
                        checked={selected.includes(result.agent_id)}
                        onChange={(event) => setSelected((current) =>
                          event.target.checked
                            ? [...current, result.agent_id]
                            : current.filter((id) => id !== result.agent_id),
                        )}
                      />
                      <span className="agent-rank">{index + 1}</span>
                      <span>
                        <a href={`/runs?agent=${result.agent_id}`}>{agent?.name ?? result.agent_id}</a>
                        <span className="cell-detail mono">{result.agent_id}</span>
                      </span>
                    </label>
                  </div>
                  <div className="agent-success">
                    <span>Success rate</span>
                    <strong>{formatRate(result.pass_rate.value)}</strong>
                    <small>{formatInterval(result.pass_rate.ci_low, result.pass_rate.ci_high)} · {result.pass_rate.passed}/{result.pass_rate.n}</small>
                  </div>
                  <div className="agent-metrics">
                    <SummaryValue
                      label="Cost (USD)"
                      value={`${formatMoney(result.cost.mean)} · ${formatMoneyInterval(result.cost.ci_low, result.cost.ci_high)}`}
                    />
                    <SummaryValue
                      label="Cost confidence"
                      value={`Verified ${result.cost_confidence.verified} · Estimated ${result.cost_confidence.estimated}`}
                    />
                    <SummaryValue label="Steps (LLM calls)" value={formatStat(result.steps.mean)} />
                    <SummaryValue label="Tool calls requested" value={formatStat(result.tool_calls.mean)} />
                    <SummaryValue label="Time (s)" value={formatStat(result.duration.mean)} />
                    <SummaryValue label="INFRA excluded" value={String(result.infra_excluded)} />
                  </div>
                </article>
              )
            })}
          </div>
          <p className="table-footnote">
            Success intervals are Wilson 95% confidence intervals. INFRA_ERROR runs are excluded;
            steps count LLM calls and tool calls count requested tools. <a href="/limitations">Metric definitions</a>.
          </p>
        </>
      )}
    </>
  )
}

function LeaderboardRow({
  result,
  selected,
  onSelect,
}: {
  result: ResultRow
  selected: boolean
  onSelect: (checked: boolean) => void
}) {
  const agent = agents.find(({ agent_id }) => agent_id === result.agent_id)
  return (
    <tr>
      <td>
        <input
          aria-label={`Select ${agent?.name ?? result.agent_id} for comparison`}
          type="checkbox"
          checked={selected}
          onChange={(event) => onSelect(event.target.checked)}
        />
      </td>
      <th scope="row">
        <a className="agent-link" href={`/runs?agent=${result.agent_id}`}>
          {agent?.name ?? result.agent_id}
          <span className="mono">{result.agent_id}</span>
        </a>
      </th>
      <td className="num">
        <strong>{formatRate(result.pass_rate.value)}</strong>
        <span className="cell-detail">{formatInterval(result.pass_rate.ci_low, result.pass_rate.ci_high)} · {result.pass_rate.passed}/{result.pass_rate.n}</span>
      </td>
      <td className="num">
        <strong>{formatMoney(result.cost.mean)}</strong>
        <span className="cell-detail">{formatMoneyInterval(result.cost.ci_low, result.cost.ci_high)}</span>
        <span className="cell-detail">
          Verified: {result.cost_confidence.verified} · Estimated: {result.cost_confidence.estimated}
        </span>
      </td>
      <td className="num">{formatStat(result.steps.mean)}</td>
      <td className="num">{formatStat(result.tool_calls.mean)}</td>
      <td className="num">{formatStat(result.duration.mean)}</td>
      <td className="num">{result.infra_excluded}</td>
    </tr>
  )
}

function Benchmarks({ benchmark }: { benchmark: Benchmark | null }) {
  return (
    <>
      <PageHeading
        title="Benchmarks"
        description="Track benchmark progress, spend, and the runs behind each result."
        action={<a className="button button-primary" href="/benchmarks/new">New benchmark</a>}
      />
      {!benchmark ? (
        <EmptyState
          title="No benchmarks yet"
          message="Create a benchmark to run agents against a shared task set."
          action={<a className="button button-primary" href="/benchmarks/new">Create benchmark</a>}
        />
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Benchmark</th>
                <th scope="col">State</th>
                <th scope="col">Progress</th>
                <th scope="col">Spend / cap</th>
                <th scope="col">Created</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row"><a href="/">{benchmark.name}</a></th>
                <td><StateBadge state={benchmark.state} /></td>
                <td>
                  <span>{benchmark.progress.done} / {benchmark.progress.total} done</span>
                  <progress
                    aria-label="Benchmark progress"
                    value={benchmark.progress.done}
                    max={Math.max(benchmark.progress.total, 1)}
                  />
                  <span className="cell-detail">
                    {benchmark.progress.infra_error} INFRA · {benchmark.progress.excluded} excluded
                  </span>
                </td>
                <td>{formatMoney(benchmark.spend_usd)} / {formatMoney(benchmark.config.spend_cap_usd)}</td>
                <td>{new Date(benchmark.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

function NewBenchmark() {
  const [message, setMessage] = useState('')
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setMessage('Mock preview only. No benchmark was launched; live API wiring is not available yet.')
  }
  return (
    <>
      <PageHeading title="New benchmark" description="Choose a shared set of agents, tasks, and scenarios." />
      <form className="launch-form" onSubmit={submit}>
        <label>
          Benchmark name
          <input required maxLength={80} defaultValue="Python repair · baseline" />
        </label>
        <label>
          Agents
          <select multiple defaultValue={agents.map(({ agent_id }) => agent_id)} size={agents.length}>
            {agents.map((agent) => <option key={agent.agent_id} value={agent.agent_id}>{agent.name}</option>)}
          </select>
        </label>
        <label>
          Tasks
          <select multiple defaultValue={tasks.map(({ task_id }) => task_id)} size={tasks.length}>
            {tasks.map((task) => <option key={task.task_id} value={task.task_id}>{task.task_id}</option>)}
          </select>
        </label>
        <label>
          Scenarios
          <select multiple defaultValue={['baseline']} size={scenarios.length}>
            {scenarios.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.id}</option>)}
          </select>
        </label>
        <div className="form-pair">
          <label>
            Runs per combination
            <input type="number" min="1" max="10" defaultValue="3" />
          </label>
          <label>
            Spend cap (USD)
            <input type="number" min="0.01" step="0.01" required defaultValue="5.00" />
          </label>
        </div>
        <button className="button button-primary" type="submit">Preview launch</button>
        {message && <p className="notice notice-info" role="status">{message}</p>}
      </form>
    </>
  )
}

function Compare({ fixture }: { fixture: DashboardFixture }) {
  const first = fixture.results[0]
  const second = fixture.results[1]
  return (
    <>
      <PageHeading title="Compare agents" description="Compare outcomes on the same task and scenario." />
      {first && second ? (
        <div className="table-scroll" role="region" aria-label="Agent comparison" tabIndex={0}>
          <table>
            <thead>
              <tr>
                <th scope="col">Task</th>
                {[first, second].map((row) => (
                  <th scope="col" key={row.agent_id}>
                    {agents.find(({ agent_id }) => agent_id === row.agent_id)?.name ?? row.agent_id}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">All tasks</th>
                {[first, second].map((row) => (
                  <td key={row.agent_id}>
                    <strong>{formatRate(row.pass_rate.value)}</strong>
                    <span className="cell-detail">{formatInterval(row.pass_rate.ci_low, row.pass_rate.ci_high)} · {row.pass_rate.passed}/{row.pass_rate.n}</span>
                    <span className="cell-detail">{formatMoney(row.cost.mean)} · {formatStat(row.steps.mean)} steps · {formatStat(row.duration.mean)} s</span>
                  </td>
                ))}
              </tr>
              <tr>
                <th scope="row">Difference</th>
                <td colSpan={2}><span className="status-pill status-neutral">No clear difference</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="Select two agents to compare"
          message="The selected fixture has fewer than two result rows."
          action={<a className="button button-secondary" href="/">View leaderboard</a>}
        />
      )}
    </>
  )
}

function RunDetailPage({ fixture }: { fixture: DashboardFixture }) {
  const run = fixture.runs[0]
  const [tab, setTab] = useState<'Timeline' | 'Diff' | 'Grader' | 'Environment'>('Timeline')
  if (!run) {
    return (
      <>
        <PageHeading title="Run detail" description="Inspect the trace and evidence for one run." />
        <EmptyState title="Run not found in this fixture" message="Choose a fixture state with a run to view its detail." />
      </>
    )
  }
  const tabs = ['Timeline', 'Diff', 'Grader', 'Environment'] as const
  return (
    <>
      <PageHeading title="Run detail" description={run.run_id} action={<StatusBadge status={run.status} />} />
      <div className="summary-grid">
        <SummaryValue label="Agent" value={agents.find(({ agent_id }) => agent_id === run.agent_id)?.name ?? run.agent_id} />
        <SummaryValue label="Task" value={run.task_id} />
        <SummaryValue label="Scenario" value={run.scenario} />
        <SummaryValue label="Model" value={run.model ?? '—'} />
        <SummaryValue label="Tokens in / out" value={`${run.tokens_in ?? '—'} / ${run.tokens_out ?? '—'}`} />
        <SummaryValue label="Cost" value={`${formatMoney(run.cost)} · ${run.cost_confidence ?? 'unknown'}`} />
        <SummaryValue label="Duration" value={run.duration === null ? '—' : `${run.duration.toFixed(1)} s`} />
        <SummaryValue label="Steps / tool calls" value={`${run.steps ?? '—'} / ${run.tool_calls ?? '—'}`} />
      </div>
      <div className="tabs" role="tablist" aria-label="Run detail sections">
        {tabs.map((item) => (
          <button
            key={item}
            type="button"
            role="tab"
            id={`run-tab-${item.toLowerCase()}`}
            aria-selected={tab === item}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <section className="tab-content" role="tabpanel" aria-labelledby={`run-tab-${tab.toLowerCase()}`}>
        <h2>{tab}</h2>
        {tab === 'Timeline' && <EventTimeline events={fixture.events} />}
        {tab === 'Diff' && <pre className="code-block">{run.workspace_diff ?? 'No workspace diff is available.'}</pre>}
        {tab === 'Grader' && <pre className="code-block">{JSON.stringify(run.grader_result, null, 2)}</pre>}
        {tab === 'Environment' && <pre className="code-block">{JSON.stringify(run.env_fingerprint, null, 2)}</pre>}
      </section>
    </>
  )
}

function RunList({ fixture }: { fixture: DashboardFixture }) {
  return (
    <>
      <PageHeading title="Runs" description="Run records for the selected benchmark and filters." />
      {fixture.runs.length ? (
        <div className="run-list">
          {fixture.runs.map((run) => (
            <a className="run-row" key={run.run_id} href={`/runs/${run.run_id}`}>
              <span>
                <strong>{agents.find(({ agent_id }) => agent_id === run.agent_id)?.name ?? run.agent_id}</strong>
                <span className="cell-detail">{run.task_id} · {run.scenario}</span>
              </span>
              <StatusBadge status={run.status} />
              <span className="mono">{run.run_id.slice(0, 8)}</span>
            </a>
          ))}
        </div>
      ) : (
        <EmptyState title="No runs match these filters" message="Choose another fixture state or clear the run filters." />
      )}
    </>
  )
}

function EventTimeline({ events }: { events: Event[] }) {
  if (!events.length) return <p className="muted-copy">No events recorded for this run.</p>
  return (
    <ol className="event-list">
      {events.map((event) => (
        <li key={event.id} className={event.type === 'fault_injected' ? 'event-fault' : ''}>
          <div className="event-topline">
            <strong>{event.type}</strong>
            <time>{new Date(event.ts).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</time>
          </div>
          <p>{event.error ?? eventSummary(event)}</p>
          <details>
            <summary>Event payload</summary>
            <pre className="code-block">{JSON.stringify(event.payload, null, 2)}</pre>
          </details>
        </li>
      ))}
    </ol>
  )
}

function Resilience({
  fixture,
  fixtureState,
}: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  const rows: ResilienceRow[] = fixture.results.map((result) => ({
    agent_id: result.agent_id,
    scenario: fixtureState === 'fault' ? 'provider_503_outage' : 'provider_503_outage',
    baseline_pass_rate: {
      passed: 11,
      n: 15,
      value: 0.733,
      ci_low: 0.48,
      ci_high: 0.89,
    },
    scenario_pass_rate: result.pass_rate,
    resilience_score: result.pass_rate.value === null ? null : result.pass_rate.value / 0.733,
  }))
  return (
    <>
      <PageHeading title="Failure scenarios" description="Compare baseline performance with selected injected faults." />
      <FixtureNotice fixture={fixture} state={fixtureState} />
      {rows.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Agent</th>
                <th scope="col">Scenario</th>
                <th scope="col">Baseline pass rate</th>
                <th scope="col">Scenario pass rate</th>
                <th scope="col">Resilience score</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.agent_id}>
                  <th scope="row">{agents.find(({ agent_id }) => agent_id === row.agent_id)?.name ?? row.agent_id}</th>
                  <td>{row.scenario}</td>
                  <td>{formatRate(row.baseline_pass_rate.value)} · {row.baseline_pass_rate.n}</td>
                  <td>{formatRate(row.scenario_pass_rate.value)} · {row.scenario_pass_rate.n}</td>
                  <td>{row.resilience_score === null ? '—' : `${(row.resilience_score * 100).toFixed(1)}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState title="No fault results" message="Choose a fixture state with results to inspect resilience." />
      )}
      <p className="table-footnote">Tests resilience under chosen conditions, not all production failures.</p>
    </>
  )
}

function Catalog() {
  return (
    <>
      <PageHeading title="Catalog" description="Agents and tasks available to benchmark." />
      <section className="content-section">
        <h2>Agents</h2>
        <div className="table-scroll">
          <table>
            <thead><tr><th scope="col">Name</th><th scope="col">Mode</th><th scope="col">Model</th><th scope="col">Description</th></tr></thead>
            <tbody>
              {agents.map((agent) => (
                <tr key={agent.agent_id}>
                  <th scope="row">{agent.name}<span className="cell-detail mono">{agent.agent_id}</span></th>
                  <td>{agent.mode}</td>
                  <td>{String(agent.model_config.model ?? '—')}</td>
                  <td>{agent.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="content-section">
        <h2>Tasks</h2>
        <div className="table-scroll">
          <table>
            <thead><tr><th scope="col">Task</th><th scope="col">Category</th><th scope="col">Grader</th><th scope="col">Validated</th><th scope="col">Weak flag</th></tr></thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.task_id}>
                  <th scope="row">{task.task_id}</th>
                  <td>{task.category}</td>
                  <td>{task.grader_type}</td>
                  <td>{task.validated ? 'Yes' : 'No'}</td>
                  <td>{task.weak === null ? 'Not assessed' : task.weak ? 'Weak' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

function Security() {
  return (
    <>
      <PageHeading title="Security" description="Security scoring is planned for a later milestone." />
      <div className="notice notice-info" role="status">
        No security assessment data is available in this scaffold. Any future score will be labelled
        as a baseline assessment, not an audit.
      </div>
    </>
  )
}

function Limitations() {
  return (
    <>
      <PageHeading title="Limitations" description="What these benchmark results can and cannot tell you." />
      <div className="limitations-list">
        <section><h2>Repeated runs are statistical</h2><p>Intervals describe uncertainty in repeated runs; small samples do not establish universal performance.</p></section>
        <section><h2>Faults are simulated</h2><p>Injected conditions cover only the selected scenarios, not every production failure.</p></section>
        <section><h2>Security is a baseline</h2><p>A benchmark security assessment is not a security audit or a guarantee of safe behavior.</p></section>
        <section><h2>Provider traffic may be unmeasurable</h2><p>Agents that hard-code provider endpoints can bypass the proxy and cannot be measured reliably.</p></section>
        <section><h2>Network and access</h2><p>The API has no authentication. Keep the service local and do not expose its ports publicly.</p></section>
        <section><h2>Metric definitions</h2><p>Steps count LLM calls. Tool calls count requested tools. INFRA_ERROR runs are excluded from statistical results.</p></section>
      </div>
    </>
  )
}

function LiveUnavailable() {
  return (
    <section className="live-unavailable" aria-labelledby="live-title">
      <p className="status-pill status-warning">Live mode</p>
      <h1 id="live-title">Live API is not connected</h1>
      <p>
        This scaffold does not make live requests. No fixture data is shown in live mode, so
        illustrative values cannot be mistaken for measured results.
      </p>
      <a className="button button-primary" href={withQuery({ mode: null })}>Return to mock data</a>
    </section>
  )
}

function EmptyState({
  title,
  message,
  action,
}: {
  title: string
  message: string
  action?: ReactNode
}) {
  return (
    <section className="empty-state" role="status">
      <h2>{title}</h2>
      <p>{message}</p>
      {action}
    </section>
  )
}

function StateBadge({ state }: { state: string }) {
  const tone = state === 'completed' ? 'positive' :
    state === 'failed' || state === 'halted_spend_cap' ? 'negative' :
      state === 'running' ? 'warning' : 'neutral'
  const label = state === 'halted_spend_cap' ? 'Halted at spend cap' : state
  return <span className={`status-pill status-${tone}`}>{label}</span>
}

function StatusBadge({ status }: { status: RunDetail['status'] }) {
  const tone = status === 'PASS' ? 'positive' :
    status === 'FAIL' ? 'negative' :
      status === 'INFRA_ERROR' ? 'warning' : 'neutral'
  return <span className={`status-pill status-${tone}`}>{status ?? 'Pending'}</span>
}

function SummaryValue({ label, value }: { label: string; value: string }) {
  return <dl className="summary-value"><dt>{label}</dt><dd>{value}</dd></dl>
}

function formatRate(value: number | null) {
  return value === null ? '—' : `${(value * 100).toFixed(1)}%`
}

function formatInterval(low: number | null, high: number | null) {
  if (low === null || high === null) return '[—]'
  return `[${(low * 100).toFixed(1)}–${(high * 100).toFixed(1)}%]`
}

function formatMoney(value: number | null) {
  return value === null ? '—' : `$${value.toFixed(4)}`
}

function formatMoneyInterval(low: number | null, high: number | null) {
  if (low === null || high === null) return '[—]'
  return `[${formatMoney(low)}–${formatMoney(high)}]`
}

function formatStat(value: number | null) {
  return value === null ? '—' : value.toFixed(1)
}

function eventSummary(event: Event) {
  const tool = event.payload.name
  const status = event.payload.status_code
  if (typeof tool === 'string') return `Requested ${tool}.`
  if (typeof status === 'number') return `HTTP ${status} · ${event.latency ?? '—'} ms`
  return `Run event recorded${event.agent_role ? ` for ${event.agent_role}` : ''}.`
}

export default App
