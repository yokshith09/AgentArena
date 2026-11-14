import type {
  Agent,
  Benchmark,
  Event,
  ResilienceRow,
  ResultRow,
  RunDetail,
  Scenario,
  TaskSummary,
} from '../types'

export type FixtureState =
  | 'success'
  | 'empty'
  | 'infra'
  | 'fault'
  | 'partial'
  | 'halted'
  | 'loading'
  | 'error'

export type DashboardFixture = {
  label: string
  benchmark: Benchmark | null
  resilience: ResilienceRow[]
  catalog: {
    agents: Agent[]
    tasks: TaskSummary[]
  }
  results: ResultRow[]
  compareResults: ResultRow[]
  runs: RunDetail[]
  events: Event[]
}

const benchmarkId = '11111111-1111-4111-8111-111111111111'
const passedRate = {
  passed: 2,
  n: 3,
  value: 0.667,
  ci_low: 0.208,
  ci_high: 0.938,
}

const makeResult = (
  agent_id: string,
  overrides: Partial<ResultRow> = {},
): ResultRow => ({
  agent_id,
  task_id: null,
  scenario: 'baseline',
  runs_counted: 3,
  infra_excluded: 0,
  pass_rate: passedRate,
  cost: {
    n: 3,
    mean: 0.004,
    median: 0.004,
    std: 0,
    ci_low: 0.004,
    ci_high: 0.004,
  },
  steps: {
    n: 3,
    mean: 6,
    median: 6,
    std: 0,
    ci_low: 6,
    ci_high: 6,
  },
  tool_calls: {
    n: 3,
    mean: 8,
    median: 8,
    std: 0,
    ci_low: 8,
    ci_high: 8,
  },
  duration: {
    n: 3,
    mean: 37.5,
    median: 37.5,
    std: 0,
    ci_low: 37.5,
    ci_high: 37.5,
  },
  cost_confidence: { verified: 3, estimated: 0 },
  ...overrides,
})

const makeBenchmark = (
  state: Benchmark['state'],
  progress: Benchmark['progress'],
  spend_usd = 0.0384,
  configOverrides: Partial<Benchmark['config']> = {},
): Benchmark => ({
  benchmark_id: benchmarkId,
  name: 'Python repair · baseline',
  state,
  config: {
    name: 'Python repair · baseline',
    agent_ids: ['agent-a-plain', 'agent-b-openai-agents', 'agent-c-test-retry'],
    task_ids: ['fix-off-by-one'],
    scenarios: ['baseline'],
    n_runs: 3,
    spend_cap_usd: 5,
    ...configOverrides,
  },
  progress,
  spend_usd,
  error: null,
  created_at: '2026-01-01T10:00:00Z',
  started_at: state === 'queued' ? null : '2026-01-01T10:00:10Z',
  finished_at: state === 'completed' || state === 'halted_spend_cap'
    ? '2026-01-01T10:08:00Z'
    : null,
})

function assertBenchmarkCounts(benchmark: Benchmark, runs: RunDetail[]) {
  const { progress, config } = benchmark
  const configuredSlots =
    config.agent_ids.length * config.task_ids.length * config.scenarios.length * config.n_runs
  const accountedSlots =
    progress.queued + progress.running + progress.done + progress.infra_error + progress.excluded
  const recordedSpend = runs.reduce((total, run) => total + (run.cost ?? 0), 0)
  console.assert(
    configuredSlots === progress.total,
    `${benchmark.name}: progress total does not match its configuration.`,
  )
  console.assert(
    accountedSlots === progress.total,
    `${benchmark.name}: progress counts do not add up to its total.`,
  )
  console.assert(
    Math.abs(recordedSpend - benchmark.spend_usd) < 0.000001,
    `${benchmark.name}: recorded run costs do not add up to its spend.`,
  )
}

const baseRun: RunDetail = {
  run_id: '22222222-2222-4222-8222-222222222222',
  benchmark_id: benchmarkId,
  agent_id: 'agent-a-plain',
  task_id: 'fix-off-by-one',
  scenario: 'baseline',
  repeat_index: 1,
  attempt: 1,
  state: 'done',
  status: 'PASS',
  passed: true,
  model: 'mock-model',
  tokens_in: 1200,
  tokens_out: 300,
  cost: 0.0042,
  cost_confidence: 'verified',
  duration: 37.5,
  steps: 6,
  tool_calls: 8,
  started_at: '2026-01-01T10:03:00Z',
  finished_at: '2026-01-01T10:03:38Z',
  error: null,
  env_fingerprint: {
    model: 'mock-model',
    date: '2026-01-01',
    task_hash: 'abc',
    pricing_version: '2026-11-11',
    agent_source_hash: null,
    python: '3.x',
    image_digest: null,
  },
  grader_result: {
    passed: true,
    tamper_detected: false,
    suites: [
      { name: 'visible', passed: true, tests_total: 4, tests_failed: 0 },
      { name: 'hidden', passed: true, tests_total: 3, tests_failed: 0 },
    ],
    summary: 'All 7 checks passed.',
    error: null,
  },
  workspace_diff: '--- a/solution.py\n+++ b/solution.py\n@@ -1,2 +1,3 @@\n-return value\n+return value + 1',
}

const secondRun: RunDetail = {
  ...baseRun,
  run_id: '33333333-3333-4333-8333-333333333333',
  repeat_index: 2,
  status: 'FAIL',
  passed: false,
  tokens_in: 980,
  tokens_out: 210,
  cost: 0.0038,
  duration: 32.4,
  error: 'The boundary condition still fails for the final element.',
  grader_result: {
    passed: false,
    tamper_detected: false,
    suites: [
      { name: 'visible', passed: false, tests_total: 4, tests_failed: 1 },
      { name: 'hidden', passed: false, tests_total: 3, tests_failed: 1 },
    ],
    summary: 'Two checks failed.',
    error: null,
  },
  workspace_diff: '--- a/solution.py\n+++ b/solution.py\n@@ -1,2 +1,2 @@\n-return value\n+return value - 1',
}

function makeRun(
  run_id: string,
  agent_id: string,
  repeat_index: number,
  status: 'PASS' | 'FAIL',
  values: Pick<RunDetail, 'cost' | 'duration' | 'steps' | 'tool_calls'>,
): RunDetail {
  const passed = status === 'PASS'
  return {
    ...baseRun,
    run_id,
    agent_id,
    repeat_index,
    status,
    passed,
    error: passed ? null : 'One or more task checks failed.',
    grader_result: passed ? baseRun.grader_result : secondRun.grader_result,
    workspace_diff: passed ? baseRun.workspace_diff : secondRun.workspace_diff,
    ...values,
  }
}

const completedRuns = [
  baseRun,
  secondRun,
  makeRun('44444444-4444-4444-8444-444444444444', 'agent-a-plain', 3, 'PASS', {
    cost: 0.004,
    duration: 42.6,
    steps: 6,
    tool_calls: 8,
  }),
  makeRun('55555555-5555-4555-8555-555555555555', 'agent-b-openai-agents', 1, 'PASS', {
    cost: 0.0038,
    duration: 34,
    steps: 6,
    tool_calls: 8,
  }),
  makeRun('66666666-6666-4666-8666-666666666666', 'agent-b-openai-agents', 2, 'PASS', {
    cost: 0.0038,
    duration: 34,
    steps: 6,
    tool_calls: 8,
  }),
  makeRun('77777777-7777-4777-8777-777777777777', 'agent-b-openai-agents', 3, 'FAIL', {
    cost: 0.0038,
    duration: 34,
    steps: 7,
    tool_calls: 8,
  }),
  makeRun('88888888-8888-4888-8888-888888888888', 'agent-c-test-retry', 1, 'PASS', {
    cost: 0.005,
    duration: 50,
    steps: 8,
    tool_calls: 10,
  }),
  makeRun('99999999-9999-4999-8999-999999999999', 'agent-c-test-retry', 2, 'FAIL', {
    cost: 0.005,
    duration: 50,
    steps: 9,
    tool_calls: 10,
  }),
  makeRun('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa', 'agent-c-test-retry', 3, 'FAIL', {
    cost: 0.005,
    duration: 50,
    steps: 8,
    tool_calls: 10,
  }),
]
const firstRuns = completedRuns.filter(({ repeat_index }) => repeat_index === 1)

const baseEvents: Event[] = [
  {
    id: 1,
    run_id: baseRun.run_id,
    ts: '2026-01-01T10:03:01Z',
    type: 'agent_started',
    agent_role: null,
    payload: { task_id: baseRun.task_id },
    latency: null,
    error: null,
  },
  {
    id: 2,
    run_id: baseRun.run_id,
    ts: '2026-01-01T10:03:08Z',
    type: 'llm_call',
    agent_role: null,
    payload: {
      endpoint: '/chat/completions',
      status_code: 200,
      model: 'mock-model',
      tokens_in: 400,
      tokens_out: 90,
      cost: 0.0012,
      cost_confidence: 'verified',
      finish_reason: 'tool_calls',
      stream: false,
    },
    latency: 2100,
    error: null,
  },
  {
    id: 3,
    run_id: baseRun.run_id,
    ts: '2026-01-01T10:03:10Z',
    type: 'tool_call',
    agent_role: null,
    payload: { name: 'run_tests', arguments_preview: '{}', call_id: 'c1' },
    latency: null,
    error: null,
  },
  {
    id: 4,
    run_id: baseRun.run_id,
    ts: '2026-01-01T10:03:38Z',
    type: 'grader_result',
    agent_role: null,
    payload: { passed: true, suite_count: 2 },
    latency: null,
    error: null,
  },
]

const agentAResult = makeResult('agent-a-plain', {
  cost: {
    n: 3,
    mean: 0.004,
    median: 0.004,
    std: 0.0002,
    ci_low: 0.0038,
    ci_high: 0.0042,
  },
  duration: {
    n: 3,
    mean: 37.5,
    median: 37.5,
    std: 5.1,
    ci_low: 32.4,
    ci_high: 42.6,
  },
})

const agentBResult = makeResult('agent-b-openai-agents', {
  pass_rate: {
    passed: 2,
    n: 3,
    value: 0.667,
    ci_low: 0.208,
    ci_high: 0.938,
  },
  cost: {
    n: 3,
    mean: 0.0038,
    median: 0.0038,
    std: 0,
    ci_low: 0.0038,
    ci_high: 0.0038,
  },
  steps: {
    n: 3,
    mean: 6.4,
    median: 6,
    std: 0.693,
    ci_low: 6,
    ci_high: 7.2,
  },
  duration: {
    n: 3,
    mean: 34,
    median: 34,
    std: 0,
    ci_low: 34,
    ci_high: 34,
  },
})

const agentCResult = makeResult('agent-c-test-retry', {
  pass_rate: {
    passed: 1,
    n: 3,
    value: 0.333,
    ci_low: 0.062,
    ci_high: 0.792,
  },
  cost: {
    n: 3,
    mean: 0.005,
    median: 0.005,
    std: 0,
    ci_low: 0.005,
    ci_high: 0.005,
  },
  steps: {
    n: 3,
    mean: 8.333,
    median: 8,
    std: 0.577,
    ci_low: 8,
    ci_high: 9,
  },
  tool_calls: {
    n: 3,
    mean: 10,
    median: 10,
    std: 0,
    ci_low: 10,
    ci_high: 10,
  },
  duration: {
    n: 3,
    mean: 50,
    median: 50,
    std: 0,
    ci_low: 50,
    ci_high: 50,
  },
})

const completed = makeBenchmark('completed', {
  total: 9,
  queued: 0,
  running: 0,
  done: 9,
  infra_error: 0,
  excluded: 0,
})
assertBenchmarkCounts(completed, completedRuns)

const completedResults = [agentAResult, agentBResult, agentCResult]
const compareResults = (results: ResultRow[]): ResultRow[] => results.map((result) => ({
  ...result,
  task_id: 'fix-off-by-one',
}))
const singleRun = (
  result: ResultRow,
  passed: boolean,
  infraExcluded = 0,
): ResultRow => ({
  ...result,
  runs_counted: 1,
  infra_excluded: infraExcluded,
  pass_rate: {
    passed: Number(passed),
    n: 1,
    value: Number(passed),
    ci_low: passed ? 0.21 : 0,
    ci_high: passed ? 1 : 0.79,
  },
  cost: { ...result.cost, n: 1 },
  steps: { ...result.steps, n: 1 },
  tool_calls: { ...result.tool_calls, n: 1 },
  duration: { ...result.duration, n: 1 },
  cost_confidence: { verified: 1, estimated: 0 },
})

const partialResults = completedResults.map((result) => {
  const run = firstRuns.find(({ agent_id }) => agent_id === result.agent_id)
  const singleResult = singleRun(result, run?.passed === true)
  if (!run) return singleResult
  return {
    ...singleResult,
    cost: { ...singleResult.cost, mean: run.cost, median: run.cost, ci_low: run.cost, ci_high: run.cost },
    steps: { ...singleResult.steps, mean: run.steps, median: run.steps, ci_low: run.steps, ci_high: run.steps },
    tool_calls: {
      ...singleResult.tool_calls,
      mean: run.tool_calls,
      median: run.tool_calls,
      ci_low: run.tool_calls,
      ci_high: run.tool_calls,
    },
    duration: {
      ...singleResult.duration,
      mean: run.duration,
      median: run.duration,
      ci_low: run.duration,
      ci_high: run.duration,
    },
  }
})
const defaultCompareResults = compareResults(completedResults)
const infraResult = singleRun(makeResult('agent-a-plain', {
  cost: {
    n: 3,
    mean: 0.0042,
    median: 0.0042,
    std: 0,
    ci_low: 0.0042,
    ci_high: 0.0042,
  },
}), true, 1)

const faultRun: RunDetail = {
  ...baseRun,
  status: 'FAIL',
  passed: false,
  scenario: 'provider_503_outage',
  error: 'Injected provider outage returned HTTP 503.',
  tokens_in: null,
  tokens_out: null,
  cost: 0,
  duration: 1,
  steps: 1,
  tool_calls: 0,
  finished_at: '2026-01-01T10:03:02Z',
}
const faultResult = singleRun(makeResult('agent-a-plain', {
  scenario: 'provider_503_outage',
  cost: {
    n: 3,
    mean: 0,
    median: 0,
    std: 0,
    ci_low: 0,
    ci_high: 0,
  },
}), false)
const noScenarioRuns: ResilienceRow['scenario_pass_rate'] = {
  passed: 0,
  n: 0,
  value: null,
  ci_low: null,
  ci_high: null,
}
const resilienceResults: ResilienceRow[] = completedResults.map((result) => {
  const scenarioPassRate = result.agent_id === 'agent-a-plain'
    ? faultResult.pass_rate
    : noScenarioRuns
  const resilienceScore =
    result.pass_rate.value === null ||
    result.pass_rate.value === 0 ||
    scenarioPassRate.value === null
      ? null
      : scenarioPassRate.value / result.pass_rate.value

  return {
    agent_id: result.agent_id,
    scenario: 'provider_503_outage',
    baseline_pass_rate: result.pass_rate,
    scenario_pass_rate: scenarioPassRate,
    resilience_score: resilienceScore,
  }
})

const faultEvents: Event[] = [
  {
    id: 1,
    run_id: faultRun.run_id,
    ts: '2026-01-01T10:03:01Z',
    type: 'fault_injected',
    agent_role: null,
    payload: {
      fault_id: 'provider_503_outage',
      group: 'provider',
      detail: 'call 1 of 3',
    },
    latency: null,
    error: null,
  },
  {
    id: 2,
    run_id: faultRun.run_id,
    ts: '2026-01-01T10:03:02Z',
    type: 'llm_call',
    agent_role: null,
    payload: {
      endpoint: '/chat/completions',
      status_code: 503,
      model: 'mock-model',
      tokens_in: null,
      tokens_out: null,
      cost: 0,
      cost_confidence: 'verified',
      stream: false,
    },
    latency: 1000,
    error: 'injected',
  },
]

export const agents: Agent[] = [
  {
    agent_id: 'agent-a-plain',
    name: 'Plain agent',
    mode: 'command',
    entrypoint: 'python agent.py',
    model_config: { model: 'mock-model' },
    description: 'A framework-free agent using the OpenAI-compatible proxy.',
  },
  {
    agent_id: 'agent-b-openai-agents',
    name: 'OpenAI Agents SDK',
    mode: 'command',
    entrypoint: 'python agent.py',
    model_config: { model: 'mock-model' },
    description: 'A coding agent built with the OpenAI Agents SDK.',
  },
  {
    agent_id: 'agent-c-test-retry',
    name: 'Test-retry agent',
    mode: 'command',
    entrypoint: 'python agent.py',
    model_config: { model: 'mock-model' },
    description: 'A framework-free agent variant with a test-retry-focused prompt.',
  },
]

export const tasks: TaskSummary[] = [
  {
    task_id: 'fix-off-by-one',
    category: 'code repair',
    prompt: 'Correct the boundary condition in the supplied Python function.',
    grader_type: 'pytest',
    faults_allowed: ['baseline', 'provider_503_outage'],
    validated: true,
    weak: null,
  },
  {
    task_id: 'handle-empty-input',
    category: 'code repair',
    prompt: 'Handle an empty input while preserving existing valid-input behavior.',
    grader_type: 'pytest',
    faults_allowed: ['baseline'],
    validated: true,
    weak: null,
  },
  {
    task_id: 'research-citations',
    category: 'research',
    prompt: 'Summarize a question using current sources and cite each claim.',
    grader_type: 'answer_match',
    faults_allowed: ['baseline'],
    validated: false,
    weak: null,
  },
]

export const scenarios: Scenario[] = [
  {
    id: 'baseline',
    group: 'baseline',
    layer: 'none',
    description: 'No fault injected.',
  },
  {
    id: 'provider_503_outage',
    group: 'provider',
    layer: 'proxy',
    description: 'Provider returns a temporary HTTP 503.',
  },
]

export const mockFixtures: Record<FixtureState, DashboardFixture> = {
  loading: {
    label: 'Loading benchmark data',
    benchmark: null,
    resilience: [],
    catalog: { agents: [], tasks: [] },
    results: [],
    compareResults: [],
    runs: [],
    events: [],
  },
  error: {
    label: 'Benchmark data unavailable',
    benchmark: null,
    resilience: [],
    catalog: { agents: [], tasks: [] },
    results: [],
    compareResults: [],
    runs: [],
    events: [],
  },
  success: {
    label: 'Completed benchmark',
    benchmark: completed,
    resilience: [],
    catalog: { agents, tasks },
    results: completedResults,
    compareResults: defaultCompareResults,
    runs: completedRuns,
    events: baseEvents,
  },
  empty: {
    label: 'Empty workspace',
    benchmark: null,
    resilience: [],
    catalog: { agents: [], tasks: [] },
    results: [],
    compareResults: [],
    runs: [],
    events: [],
  },
  infra: {
    label: 'Infrastructure exclusion',
    benchmark: makeBenchmark('completed', {
      total: 2,
      queued: 0,
      running: 0,
      done: 1,
      infra_error: 1,
      excluded: 0,
    }, 0.0042, {
      agent_ids: ['agent-a-plain'],
      n_runs: 2,
    }),
    resilience: [],
    catalog: { agents, tasks },
    results: [infraResult],
    compareResults: compareResults([infraResult]),
    runs: [
      baseRun,
      {
        ...baseRun,
        run_id: 'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
        repeat_index: 2,
        status: 'INFRA_ERROR',
        passed: null,
        error: 'Runner could not start.',
        tokens_in: null,
        tokens_out: null,
        cost: 0,
        duration: null,
        steps: null,
        tool_calls: null,
        grader_result: null,
        workspace_diff: null,
      },
    ],
    events: [],
  },
  fault: {
    label: 'Injected provider fault',
    benchmark: makeBenchmark('completed', {
      total: 1,
      queued: 0,
      running: 0,
      done: 1,
      infra_error: 0,
      excluded: 0,
    }, 0, {
      agent_ids: ['agent-a-plain'],
      scenarios: ['provider_503_outage'],
      n_runs: 1,
    }),
    resilience: resilienceResults,
    catalog: { agents, tasks },
    results: [faultResult],
    compareResults: compareResults([faultResult]),
    runs: [faultRun],
    events: faultEvents,
  },
  partial: {
    label: 'Results in progress',
    benchmark: makeBenchmark('running', {
      total: 9,
      queued: 4,
      running: 2,
      done: 3,
      infra_error: 0,
      excluded: 0,
    }, 0.013),
    resilience: [],
    catalog: { agents, tasks },
    results: partialResults,
    compareResults: compareResults(partialResults),
    runs: firstRuns,
    events: baseEvents,
  },
  halted: {
    label: 'Stopped at spend cap',
    benchmark: makeBenchmark('halted_spend_cap', {
      total: 9,
      queued: 6,
      running: 0,
      done: 3,
      infra_error: 0,
      excluded: 0,
    }, 0.013, { spend_cap_usd: 0.01 }),
    resilience: [],
    catalog: { agents, tasks },
    results: partialResults,
    compareResults: compareResults(partialResults),
    runs: firstRuns,
    events: baseEvents,
  },
}

Object.values(mockFixtures).forEach(({ benchmark, runs }) => {
  if (benchmark) assertBenchmarkCounts(benchmark, runs)
})
