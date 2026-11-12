import { useState, type FormEvent, type ReactNode } from 'react'
import {
  agents,
  mockFixtures,
  scenarios,
  type DashboardFixture,
  type FixtureState,
} from './mocks/fixtures'
import FixtureNotice from './components/FixtureNotice'
import RunDetailPage from './components/RunDetail'
import type { ResilienceRow, ResultRow, RunDetail } from './types'
import './App.css'

const stateOptions: Array<{ value: FixtureState; label: string }> = [
  { value: 'success', label: 'Completed' },
  { value: 'empty', label: 'Empty' },
  { value: 'infra', label: 'INFRA excluded' },
  { value: 'fault', label: 'Fault injected' },
  { value: 'partial', label: 'In progress' },
  { value: 'halted', label: 'Spend cap halted' },
  { value: 'loading', label: 'Loading' },
  { value: 'error', label: 'Error' },
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

const routeTitles: Record<Route, string> = {
  leaderboard: 'Leaderboard',
  benchmarks: 'Benchmarks',
  'new-benchmark': 'New benchmark',
  compare: 'Compare agents',
  'run-detail': 'Run detail',
  'run-list': 'Runs',
  resilience: 'Failure scenarios',
  catalog: 'Catalog',
  security: 'Security',
  limitations: 'Limitations',
}

const routeDescriptions: Record<Route, string> = {
  leaderboard: 'Agent performance across the selected benchmark.',
  benchmarks: 'Track benchmark progress, spend, and the runs behind each result.',
  'new-benchmark': 'Choose a shared set of agents, tasks, and scenarios.',
  compare: 'Compare outcomes on the same task and scenario.',
  'run-detail': 'Inspect the trace and evidence for one run.',
  'run-list': 'Run records for the selected benchmark and filters.',
  resilience: 'Compare baseline performance with selected injected faults.',
  catalog: 'Agents and tasks available to benchmark.',
  security: 'Security scoring is planned for a later milestone.',
  limitations: 'What these benchmark results can and cannot tell you.',
}

function isFixtureState(value: string | null): value is FixtureState {
  return stateOptions.some(({ value: state }) => state === value)
}

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

function routeHref(path: string, changes: Record<string, string | null>) {
  const params = new URLSearchParams(window.location.search)
  Object.entries(changes).forEach(([key, value]) => {
    if (value) params.set(key, value)
    else params.delete(key)
  })
  const query = params.toString()
  return `${path}${query ? `?${query}` : ''}`
}

function withQuery(changes: Record<string, string | null>) {
  return routeHref(window.location.pathname, changes)
}

function App() {
  const route = getRoute(window.location.pathname)
  const params = new URLSearchParams(window.location.search)
  const requestedState = params.get('state')
  const fixtureState = isFixtureState(requestedState) ? requestedState : 'success'
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
  if (route !== 'limitations' && fixtureState === 'loading') {
    return <FixtureLoading title={routeTitles[route]} description={routeDescriptions[route]} />
  }
  if (route !== 'limitations' && fixtureState === 'error') {
    return <FixtureError title={routeTitles[route]} description={routeDescriptions[route]} />
  }

  switch (route) {
    case 'leaderboard':
      return <Leaderboard fixture={fixture} fixtureState={fixtureState} />
    case 'benchmarks':
      return <Benchmarks fixture={fixture} fixtureState={fixtureState} />
    case 'new-benchmark':
      return <NewBenchmark fixture={fixture} fixtureState={fixtureState} />
    case 'compare':
      return <Compare fixture={fixture} fixtureState={fixtureState} />
    case 'run-detail':
      return <RunDetailPage fixture={fixture} fixtureState={fixtureState} />
    case 'run-list':
      return <RunList fixture={fixture} fixtureState={fixtureState} />
    case 'resilience':
      return <Resilience fixture={fixture} fixtureState={fixtureState} />
    case 'catalog':
      return <Catalog fixtureState={fixtureState} fixture={fixture} />
    case 'security':
      return <Security fixtureState={fixtureState} fixture={fixture} />
    case 'limitations':
      return <Limitations />
  }
}

function FixtureLoading({ title, description }: { title: string; description: string }) {
  return (
    <>
      <PageHeading title={title} description={description} />
      <section
        className="loading-region"
        role="status"
        aria-label={`Loading ${title.toLowerCase()}`}
        aria-busy="true"
      >
        <span className="sr-only">Loading {title.toLowerCase()} data.</span>
        <div className="loading-heading" aria-hidden="true">
          <span />
          <span />
        </div>
        <div className="loading-row" aria-hidden="true"><span /><span /></div>
        <div className="loading-row" aria-hidden="true"><span /><span /></div>
        <div className="loading-row" aria-hidden="true"><span /><span /></div>
      </section>
    </>
  )
}

function FixtureError({ title, description }: { title: string; description: string }) {
  return (
    <>
      <PageHeading title={title} description={description} />
      <section className="fixture-error-state" role="alert" aria-labelledby="fixture-error-title">
        <h2 id="fixture-error-title">Could not load {title.toLowerCase()} data</h2>
        <p>This simulated fixture error made no live API request.</p>
        <a className="button button-secondary" href={withQuery({ state: 'success' })}>
          Return to completed fixture
        </a>
      </section>
    </>
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

function Leaderboard({
  fixture,
  fixtureState,
}: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  const [selected, setSelected] = useState<string[]>([])
  const query = new URLSearchParams(window.location.search)
  const availableScenarios = [...new Set(fixture.results.map(({ scenario }) => scenario))]
  const requestedScenario = query.get('scenario')
  const selectedScenario = availableScenarios.find((scenarioId) => scenarioId === requestedScenario) ??
    availableScenarios[0] ?? 'baseline'
  const results = fixture.results.filter(({ scenario }) => scenario === selectedScenario)
  const selectedInScope = selected.filter((id) => results.some(({ agent_id }) => agent_id === id))
  const compareHref = routeHref('/compare', {
    agents: selectedInScope.join(','),
    benchmark: fixture.benchmark?.benchmark_id ?? null,
    scenario: selectedScenario,
  })
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
              <select
                id="scenario"
                value={selectedScenario}
                onChange={(event) => {
                  window.location.href = withQuery({ scenario: event.target.value })
                }}
              >
                {availableScenarios.map((scenarioId) => (
                  <option key={scenarioId} value={scenarioId}>{scenarioId}</option>
                ))}
              </select>
            </div>
            <span>{results.length} agents · generated Jan 1, 2026</span>
          </div>
          {selectedInScope.length > 1 && (
            <a className="button button-secondary compare-action" href={compareHref}>
              Compare {selectedInScope.length} agents
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
                {results.map((result) => (
                  <LeaderboardRow
                    key={result.agent_id}
                    result={result}
                    benchmarkId={fixture.benchmark?.benchmark_id ?? null}
                    selected={selectedInScope.includes(result.agent_id)}
                    selectionDisabled={!selectedInScope.includes(result.agent_id) && selectedInScope.length >= 3}
                    onSelect={(checked) => setSelected((current) =>
                      checked
                        ? current.includes(result.agent_id) ? current : [...current, result.agent_id]
                        : current.filter((id) => id !== result.agent_id),
                    )}
                  />
                ))}
              </tbody>
            </table>
          </div>
          <div className="mobile-leaderboard" aria-label="Leaderboard results">
            {results.map((result, index) => {
              const agent = agents.find(({ agent_id }) => agent_id === result.agent_id)
              return (
                <article className="agent-summary" key={result.agent_id}>
                  <div className="agent-summary-heading">
                    <label className="agent-summary-select">
                      <input
                        aria-label={`Select ${agent?.name ?? result.agent_id} for comparison`}
                        type="checkbox"
                        checked={selectedInScope.includes(result.agent_id)}
                        disabled={!selectedInScope.includes(result.agent_id) && selectedInScope.length >= 3}
                        onChange={(event) => setSelected((current) =>
                          event.target.checked
                            ? current.includes(result.agent_id) ? current : [...current, result.agent_id]
                            : current.filter((id) => id !== result.agent_id),
                        )}
                      />
                      <span className="agent-rank">{index + 1}</span>
                      <span>
                        <a href={routeHref('/runs', {
                          agent: result.agent_id,
                          scenario: result.scenario,
                          benchmark: fixture.benchmark?.benchmark_id ?? null,
                        })}>{agent?.name ?? result.agent_id}</a>
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
  benchmarkId,
  selected,
  selectionDisabled,
  onSelect,
}: {
  result: ResultRow
  benchmarkId: string | null
  selected: boolean
  selectionDisabled: boolean
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
          disabled={selectionDisabled}
          onChange={(event) => onSelect(event.target.checked)}
        />
      </td>
      <th scope="row">
        <a className="agent-link" href={routeHref('/runs', {
          agent: result.agent_id,
          task: result.task_id,
          scenario: result.scenario,
          benchmark: benchmarkId,
        })}>
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

function Benchmarks({
  fixture,
  fixtureState,
}: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  const { benchmark } = fixture
  return (
    <>
      <PageHeading
        title="Benchmarks"
        description="Track benchmark progress, spend, and the runs behind each result."
        action={<a className="button button-primary" href="/benchmarks/new">New benchmark</a>}
      />
      <FixtureNotice fixture={fixture} state={fixtureState} />
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
                <th scope="col">Runs</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">
                  <a href={routeHref('/', { benchmark: benchmark.benchmark_id })}>{benchmark.name}</a>
                </th>
                <td><StateBadge state={benchmark.state} /></td>
                <td>
                  <span>{benchmark.progress.done} / {benchmark.progress.total} done</span>
                  <progress
                    aria-label="Benchmark progress"
                    value={benchmark.progress.done}
                    max={Math.max(benchmark.progress.total, 1)}
                  />
                  <span className="cell-detail">
                    {benchmark.progress.running} running · {benchmark.progress.queued} queued
                  </span>
                  <span className="cell-detail">
                    {benchmark.progress.infra_error} INFRA · {benchmark.progress.excluded} excluded
                  </span>
                </td>
                <td className="num">
                  <strong>{formatMoney(benchmark.spend_usd)}</strong>
                  <span className="cell-detail">of {formatMoney(benchmark.config.spend_cap_usd)}</span>
                </td>
                <td>{new Date(benchmark.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</td>
                <td>
                  <a href={routeHref('/runs', { benchmark: benchmark.benchmark_id })}>View runs</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </>
  )
}

function NewBenchmark({
  fixture,
  fixtureState,
}: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  const [message, setMessage] = useState('')
  const [name, setName] = useState('Python repair · baseline')
  const [selectedAgentIds, setSelectedAgentIds] = useState(
    fixture.catalog.agents.map(({ agent_id }) => agent_id),
  )
  const [selectedTaskIds, setSelectedTaskIds] = useState(
    fixture.catalog.tasks.filter(({ validated }) => validated).map(({ task_id }) => task_id),
  )
  const [selectedScenarioIds, setSelectedScenarioIds] = useState(['baseline'])
  const [runsPerCombination, setRunsPerCombination] = useState('3')
  const [spendCap, setSpendCap] = useState('5.00')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const catalogAgents = fixture.catalog.agents
  const catalogTasks = fixture.catalog.tasks
  const selectedTasks = catalogTasks.filter(({ task_id }) => selectedTaskIds.includes(task_id))
  const scenarioAllowed = (scenarioId: string, taskIds = selectedTaskIds) =>
    scenarioId === 'baseline' ||
    (taskIds.length > 0 &&
      catalogTasks
        .filter(({ task_id }) => taskIds.includes(task_id))
        .every(({ faults_allowed }) => faults_allowed.includes(scenarioId)))

  function clearFeedback(...fields: string[]) {
    setErrors((current) => {
      const next = { ...current }
      fields.forEach((field) => delete next[field])
      return next
    })
    setMessage('')
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const nextErrors: Record<string, string> = {}
    const runCount = Number(runsPerCombination)
    const cap = Number(spendCap)
    if (!name.trim()) nextErrors.name = 'Enter a benchmark name.'
    if (selectedAgentIds.length === 0) nextErrors.agents = 'Select at least one agent.'
    if (selectedTaskIds.length === 0) nextErrors.tasks = 'Select at least one validated task.'
    if (selectedTasks.some(({ validated }) => !validated)) {
      nextErrors.tasks = 'Every selected task must be validated.'
    }
    if (selectedScenarioIds.length === 0) nextErrors.scenarios = 'Select at least one scenario.'
    if (selectedScenarioIds.some((scenarioId) => !scenarioAllowed(scenarioId))) {
      nextErrors.scenarios = 'Each scenario must be allowed by every selected task.'
    }
    if (!Number.isInteger(runCount) || runCount < 1 || runCount > 10) {
      nextErrors.runs = 'Enter a whole number from 1 to 10.'
    }
    if (!Number.isFinite(cap) || cap <= 0) {
      nextErrors.spend = 'Enter a spend cap greater than $0.'
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      setMessage('')
      return
    }
    const slots = selectedAgentIds.length * selectedTaskIds.length *
      selectedScenarioIds.length * runCount
    setMessage(`Mock preview ready: ${slots} run slots. No benchmark was queued.`)
  }
  return (
    <>
      <PageHeading title="New benchmark" description="Choose a shared set of agents, tasks, and scenarios." />
      <FixtureNotice fixture={fixture} state={fixtureState} />
      {catalogAgents.length === 0 || catalogTasks.length === 0 ? (
        <EmptyState
          title="Agents and tasks are required"
          message="Add an agent and a validated task before configuring a benchmark."
          action={<a className="button button-secondary" href="/catalog">Open catalog</a>}
        />
      ) : (
        <form className="launch-form" noValidate onSubmit={submit}>
          <label htmlFor="benchmark-name">
            Benchmark name
            <input
              id="benchmark-name"
              maxLength={80}
              value={name}
              aria-invalid={Boolean(errors.name)}
              aria-describedby={errors.name ? 'benchmark-name-error' : undefined}
              onChange={(event) => {
                setName(event.target.value)
                clearFeedback('name')
              }}
            />
            {errors.name && <span id="benchmark-name-error" className="form-error">{errors.name}</span>}
          </label>
          <fieldset>
            <legend>Agents</legend>
            <select
              aria-label="Agents"
              multiple
              value={selectedAgentIds}
              size={Math.min(catalogAgents.length, 4)}
              aria-invalid={Boolean(errors.agents)}
              aria-describedby={errors.agents ? 'benchmark-agents-error' : undefined}
              onChange={(event) => {
                setSelectedAgentIds(
                  Array.from(event.currentTarget.selectedOptions, ({ value }) => value),
                )
                clearFeedback('agents')
              }}
            >
              {catalogAgents.map((agent) => <option key={agent.agent_id} value={agent.agent_id}>{agent.name}</option>)}
            </select>
            {errors.agents && <span id="benchmark-agents-error" className="form-error">{errors.agents}</span>}
          </fieldset>
          <fieldset>
            <legend>Tasks</legend>
            <select
              aria-label="Tasks"
              multiple
              value={selectedTaskIds}
              size={Math.min(catalogTasks.length, 4)}
              aria-invalid={Boolean(errors.tasks)}
              aria-describedby={errors.tasks ? 'benchmark-tasks-error' : undefined}
              onChange={(event) => {
                const nextTaskIds = Array.from(
                  event.currentTarget.selectedOptions,
                  ({ value }) => value,
                )
                setSelectedTaskIds(nextTaskIds)
                clearFeedback('tasks', 'scenarios')
                setSelectedScenarioIds((current) =>
                  current.filter((scenarioId) => scenarioAllowed(scenarioId, nextTaskIds)),
                )
              }}
            >
              {catalogTasks.map((task) => (
                <option key={task.task_id} value={task.task_id} disabled={!task.validated}>
                  {task.task_id}{task.validated ? '' : ' (not validated)'}
                </option>
              ))}
            </select>
            {errors.tasks && <span id="benchmark-tasks-error" className="form-error">{errors.tasks}</span>}
          </fieldset>
          <fieldset>
            <legend>Scenarios</legend>
            <select
              aria-label="Scenarios"
              multiple
              value={selectedScenarioIds}
              size={Math.min(scenarios.length, 4)}
              aria-invalid={Boolean(errors.scenarios)}
              aria-describedby={errors.scenarios ? 'benchmark-scenarios-error' : undefined}
              onChange={(event) => {
                setSelectedScenarioIds(
                  Array.from(event.currentTarget.selectedOptions, ({ value }) => value),
                )
                clearFeedback('scenarios')
              }}
            >
              {scenarios.map((scenario) => {
                const allowed = scenarioAllowed(scenario.id)
                return (
                  <option key={scenario.id} value={scenario.id} disabled={!allowed}>
                    {scenario.id}{allowed ? '' : ' (disallowed)'}
                  </option>
                )
              })}
            </select>
            {scenarios.some(({ id }) => !scenarioAllowed(id)) && (
              <p className="field-hint">Fault scenarios are disabled until every selected task allows them.</p>
            )}
            {errors.scenarios && <span id="benchmark-scenarios-error" className="form-error">{errors.scenarios}</span>}
          </fieldset>
          <div className="form-pair">
            <label htmlFor="runs-per-combination">
              Runs per combination
              <input
                id="runs-per-combination"
                type="number"
                min="1"
                max="10"
                step="1"
                value={runsPerCombination}
                aria-invalid={Boolean(errors.runs)}
                aria-describedby={errors.runs ? 'runs-error' : undefined}
                onChange={(event) => {
                  setRunsPerCombination(event.target.value)
                  clearFeedback('runs')
                }}
              />
              {errors.runs && <span id="runs-error" className="form-error">{errors.runs}</span>}
            </label>
            <label htmlFor="spend-cap">
              Spend cap (USD)
              <input
                id="spend-cap"
                type="number"
                min="0"
                step="any"
                value={spendCap}
                aria-invalid={Boolean(errors.spend)}
                aria-describedby={errors.spend ? 'spend-error' : undefined}
                onChange={(event) => {
                  setSpendCap(event.target.value)
                  clearFeedback('spend')
                }}
              />
              {errors.spend && <span id="spend-error" className="form-error">{errors.spend}</span>}
            </label>
          </div>
          <div className="launch-preview">
            <strong>Mock preview</strong>
            <span>
              {selectedAgentIds.length * selectedTaskIds.length * selectedScenarioIds.length *
                (Number(runsPerCombination) || 0)} planned run slots
            </span>
            <span>No benchmark will be queued by this preview.</span>
          </div>
          <button className="button button-primary" type="submit">Preview launch</button>
          {Object.keys(errors).length > 0 && (
            <p className="form-error-summary" role="alert">Correct the highlighted fields before previewing.</p>
          )}
          {message && <p className="notice notice-info" role="status">{message}</p>}
        </form>
      )}
    </>
  )
}

function Compare({
  fixture,
  fixtureState,
}: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  const taskResults = fixture.compareResults
  const pooledResults = fixture.results
  const availableScenarios = [...new Set(
    [...pooledResults, ...taskResults].map(({ scenario }) => scenario),
  )]
  const query = new URLSearchParams(window.location.search)
  const requestedScenario = query.get('scenario')
  const [scenario, setScenario] = useState(
    availableScenarios.find((scenarioId) => scenarioId === requestedScenario) ??
      availableScenarios[0] ?? 'baseline',
  )
  const scenarioResults = taskResults.filter((row) => row.scenario === scenario)
  const pooledScenarioResults = pooledResults.filter((row) => row.scenario === scenario)
  const availableAgentIds = [...new Set(scenarioResults.map(({ agent_id }) => agent_id))]
  const requestedAgentIds = (query.get('agents') ?? '')
    .split(',')
    .filter((agentId, index, values) => agentId && values.indexOf(agentId) === index)
  const [selectedAgentIds, setSelectedAgentIds] = useState(() => {
    const requested = requestedAgentIds.filter((agentId) => availableAgentIds.includes(agentId))
    return requested.length >= 2 ? requested.slice(0, 3) : availableAgentIds.slice(0, 2)
  })
  const selectedRows = selectedAgentIds
    .map((agentId) => pooledScenarioResults.find(({ agent_id }) => agent_id === agentId))
    .filter((row): row is ResultRow => row !== undefined)
  const taskIds = [...new Set(scenarioResults.flatMap((row) =>
    selectedAgentIds.includes(row.agent_id) && row.task_id ? [row.task_id] : [],
  ))]
  const comparisonRows = [
    { key: 'all', label: 'All tasks', rows: selectedRows },
    ...taskIds.map((taskId) => ({
      key: taskId,
      label: taskId,
      rows: scenarioResults.filter(
        (row) => row.task_id === taskId && selectedAgentIds.includes(row.agent_id),
      ),
    })),
  ]

  return (
    <>
      <PageHeading title="Compare agents" description="Compare outcomes on the same task and scenario." />
      <FixtureNotice fixture={fixture} state={fixtureState} />
      <div className="compare-controls">
        <label className="scenario-control" htmlFor="compare-scenario">
          Scenario
          <select
            id="compare-scenario"
            value={scenario}
            disabled={availableScenarios.length < 2}
            onChange={(event) => {
              const nextScenario = event.target.value
              const nextRows = taskResults.filter((row) => row.scenario === nextScenario)
              const nextAgentIds = [...new Set(nextRows.map(({ agent_id }) => agent_id))]
              const retained = selectedAgentIds.filter((agentId) => nextAgentIds.includes(agentId))
              const nextSelectedAgentIds = retained.length >= 2
                ? retained.slice(0, 3)
                : nextAgentIds.slice(0, 2)
              setScenario(nextScenario)
              setSelectedAgentIds(nextSelectedAgentIds)
              window.history.replaceState(null, '', routeHref('/compare', {
                scenario: nextScenario,
                agents: nextSelectedAgentIds.join(','),
              }))
            }}
          >
            {availableScenarios.map((scenarioId) => (
              <option key={scenarioId} value={scenarioId}>{scenarioId}</option>
            ))}
          </select>
        </label>
        <fieldset className="compare-agent-picker">
          <legend>Agents to compare (choose 2–3)</legend>
          {availableAgentIds.map((agentId) => {
            const checked = selectedAgentIds.includes(agentId)
            const agentName = agents.find(({ agent_id }) => agent_id === agentId)?.name ?? agentId
            return (
              <label key={agentId}>
                <input
                  type="checkbox"
                  checked={checked}
                  disabled={!checked && selectedAgentIds.length >= 3}
                  onChange={(event) => {
                    const nextSelectedAgentIds = event.target.checked
                      ? [...selectedAgentIds, agentId]
                      : selectedAgentIds.filter((id) => id !== agentId)
                    setSelectedAgentIds(nextSelectedAgentIds)
                    window.history.replaceState(null, '', routeHref('/compare', {
                      agents: nextSelectedAgentIds.join(','),
                      scenario,
                    }))
                  }}
                />
                {agentName}
              </label>
            )
          })}
        </fieldset>
      </div>
      {selectedAgentIds.length >= 2 ? (
        <>
          <div className="table-scroll" role="region" aria-label="Agent comparison" tabIndex={0}>
            <table className="comparison-table">
              <thead>
                <tr>
                  <th scope="col">Task</th>
                  {selectedAgentIds.map((agentId, index) => (
                    <th
                      scope="col"
                      key={agentId}
                      className={index === 2 ? 'compare-third-column' : undefined}
                    >
                      {agents.find(({ agent_id }) => agent_id === agentId)?.name ?? agentId}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {comparisonRows.map(({ key, label, rows }) => {
                  const winner = clearWinner(rows, selectedAgentIds.length)
                  return (
                    <ComparisonRows
                      key={key}
                      label={label}
                      rows={rows}
                      selectedAgentIds={selectedAgentIds}
                      winner={winner}
                      scenario={scenario}
                      benchmarkId={fixture.benchmark?.benchmark_id ?? null}
                    />
                  )
                })}
              </tbody>
            </table>
          </div>
          {selectedAgentIds.length === 3 && (
            <section className="third-agent-stack" aria-label="Third agent comparison">
              <h2>
                {agents.find(({ agent_id }) => agent_id === selectedAgentIds[2])?.name ??
                  selectedAgentIds[2]}
              </h2>
              {comparisonRows.map(({ key, label, rows }) => {
                const row = rows.find(({ agent_id }) => agent_id === selectedAgentIds[2])
                const winner = clearWinner(rows, selectedAgentIds.length)
                return (
                  <div className="third-agent-row" key={key}>
                    <strong>{label}</strong>
                    {row ? (
                      <>
                        <span>
                          {formatRate(row.pass_rate.value)} · {formatInterval(row.pass_rate.ci_low, row.pass_rate.ci_high)}
                        </span>
                        <span>
                          {formatMoney(row.cost.mean)} · {formatStat(row.steps.mean)} steps · {formatStat(row.duration.mean)} s
                        </span>
                        <a href={routeHref('/runs', {
                          agent: row.agent_id,
                          task: row.task_id,
                          scenario,
                          benchmark: fixture.benchmark?.benchmark_id ?? null,
                          agents: null,
                        })}>View runs</a>
                      </>
                    ) : <span className="cell-detail">No result</span>}
                    <span className="cell-detail">
                      {winner
                        ? `${agents.find(({ agent_id }) => agent_id === winner)?.name ?? winner} leads`
                        : 'No clear difference'}
                    </span>
                  </div>
                )
              })}
            </section>
          )}
        </>
      ) : (
        <EmptyState
          title={availableAgentIds.length < 2 ? 'Not enough agents to compare' : 'Select two agents to compare'}
          message={availableAgentIds.length < 2
            ? 'Choose a fixture with results for at least two agents.'
            : 'Select two or three agents to compare their outcomes.'}
          action={<a className="button button-secondary" href="/">View leaderboard</a>}
        />
      )}
    </>
  )
}

function ComparisonRows({
  label,
  rows,
  selectedAgentIds,
  winner,
  scenario,
  benchmarkId,
}: {
  label: string
  rows: ResultRow[]
  selectedAgentIds: string[]
  winner: string | null
  scenario: string
  benchmarkId: string | null
}) {
  const winnerName = winner
    ? agents.find(({ agent_id }) => agent_id === winner)?.name ?? winner
    : null
  return (
    <>
      <tr>
        <th scope="row">{label}</th>
        {selectedAgentIds.map((agentId, index) => {
          const row = rows.find(({ agent_id }) => agent_id === agentId)
          return (
            <td
              key={agentId}
              className={[
                winner === agentId ? 'compare-winner' : '',
                index === 2 ? 'compare-third-column' : '',
              ].filter(Boolean).join(' ')}
            >
              {row ? (
                <>
                  <strong>{formatRate(row.pass_rate.value)}</strong>
                  <span className="cell-detail">
                    {formatInterval(row.pass_rate.ci_low, row.pass_rate.ci_high)} · {row.pass_rate.passed}/{row.pass_rate.n}
                  </span>
                  <span className="cell-detail">
                    {formatMoney(row.cost.mean)} · {formatStat(row.steps.mean)} steps · {formatStat(row.duration.mean)} s
                  </span>
                  <a className="cell-run-link" href={routeHref('/runs', {
                    agent: row.agent_id,
                    task: row.task_id,
                    scenario,
                    benchmark: benchmarkId,
                    agents: null,
                  })}>View runs</a>
                </>
              ) : <span className="cell-detail">No result</span>}
            </td>
          )
        })}
      </tr>
      <tr className="comparison-outcome">
        <th scope="row">Difference</th>
        <td colSpan={selectedAgentIds.length}>
          {winnerName
            ? `${winnerName} leads; its 95% interval does not overlap the others.`
            : 'No clear difference: the 95% intervals overlap or results are missing.'}
        </td>
      </tr>
    </>
  )
}

function clearWinner(rows: ResultRow[], expectedCount: number): string | null {
  if (
    rows.length !== expectedCount ||
    rows.some((row) =>
      row.pass_rate.value === null ||
      row.pass_rate.ci_low === null ||
      row.pass_rate.ci_high === null,
    )
  ) return null
  const ranked = [...rows].sort(
    (first, second) => (second.pass_rate.value ?? 0) - (first.pass_rate.value ?? 0),
  )
  const top = ranked[0]
  const topIntervalLow = top.pass_rate.ci_low
  if (topIntervalLow === null) return null
  const hasSeparatedInterval = ranked
    .slice(1)
    .every((row) => row.pass_rate.ci_high !== null && topIntervalLow > row.pass_rate.ci_high)
  return hasSeparatedInterval ? top.agent_id : null
}

function RunList({
  fixture,
  fixtureState,
}: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  const query = new URLSearchParams(window.location.search)
  const filters = {
    agent: query.get('agent'),
    task: query.get('task'),
    scenario: query.get('scenario'),
    status: query.get('status'),
    benchmark: query.get('benchmark'),
  }
  const activeFilters = Object.entries(filters).filter(([, value]) => value)
  const runs = fixture.runs.filter((run) =>
    (!filters.agent || run.agent_id === filters.agent) &&
    (!filters.task || run.task_id === filters.task) &&
    (!filters.scenario || run.scenario === filters.scenario) &&
    (!filters.status || run.status === filters.status) &&
    (!filters.benchmark || run.benchmark_id === filters.benchmark),
  )
  return (
    <>
      <PageHeading title="Runs" description="Run records for the selected benchmark and filters." />
      <FixtureNotice fixture={fixture} state={fixtureState} />
      {activeFilters.length > 0 && (
        <p className="run-filter-summary">
          {runs.length} matching runs · {activeFilters.map(([key, value]) => `${key}: ${value}`).join(' · ')}
          {' '}<a href={routeHref('/runs', {
            agent: null,
            task: null,
            scenario: null,
            status: null,
            benchmark: null,
            agents: null,
          })}>Clear filters</a>
        </p>
      )}
      {runs.length ? (
        <div className="run-list">
          {runs.map((run) => (
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
        <EmptyState
          title="No runs match these filters"
          message="Choose another fixture state or clear the run filters."
          action={activeFilters.length > 0
            ? <a className="button button-secondary" href={routeHref('/runs', {
                agent: null,
                task: null,
                scenario: null,
                status: null,
                benchmark: null,
                agents: null,
              })}>Clear filters</a>
            : undefined}
        />
      )}
    </>
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
    scenario: 'provider_503_outage',
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

function Catalog({ fixture, fixtureState }: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  return (
    <>
      <PageHeading title="Catalog" description="Agents and tasks available to benchmark." />
      <FixtureNotice fixture={fixture} state={fixtureState} />
      <section className="content-section">
        <h2>Agents</h2>
        <div className="table-scroll">
          <table>
            <thead><tr><th scope="col">Name</th><th scope="col">Mode</th><th scope="col">Model</th><th scope="col">Description</th></tr></thead>
            <tbody>
              {fixture.catalog.agents.map((agent) => (
                <tr key={agent.agent_id}>
                  <th scope="row">{agent.name}<span className="cell-detail mono">{agent.agent_id}</span></th>
                  <td>{agent.mode}</td>
                  <td>{String(agent.model_config.model ?? '—')}</td>
                  <td>{agent.description}</td>
                </tr>
              ))}
              {fixture.catalog.agents.length === 0 && (
                <tr><td colSpan={4}>No agents registered.</td></tr>
              )}
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
              {fixture.catalog.tasks.map((task) => (
                <tr key={task.task_id}>
                  <th scope="row">{task.task_id}</th>
                  <td>{task.category}</td>
                  <td>{task.grader_type}</td>
                  <td>{task.validated ? 'Yes' : 'No'}</td>
                  <td>{task.weak === null ? 'Not assessed' : task.weak ? 'Weak' : 'No'}</td>
                </tr>
              ))}
              {fixture.catalog.tasks.length === 0 && (
                <tr><td colSpan={5}>No tasks are available.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </>
  )
}

function Security({ fixture, fixtureState }: {
  fixture: DashboardFixture
  fixtureState: FixtureState
}) {
  return (
    <>
      <PageHeading title="Security" description="Security scoring is planned for a later milestone." />
      <FixtureNotice fixture={fixture} state={fixtureState} />
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

export default App
