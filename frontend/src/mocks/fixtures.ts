import type {
  Agent,
  Benchmark,
  Event,
  ResultRow,
  RunDetail,
  Scenario,
  TaskSummary,
} from '../types'

export type FixtureState = 'success' | 'empty' | 'infra' | 'fault' | 'partial' | 'halted'

export type DashboardFixture = {
  label: string
  benchmark: Benchmark | null
  results: ResultRow[]
  runs: RunDetail[]
  events: Event[]
}

const benchmarkId = '11111111-1111-4111-8111-111111111111'
const passedRate = {
  passed: 11,
  n: 15,
  value: 0.733,
  ci_low: 0.48,
  ci_high: 0.89,
}

const makeResult = (
  agent_id: string,
  overrides: Partial<ResultRow> = {},
): ResultRow => ({
  agent_id,
  task_id: null,
  scenario: 'baseline',
  runs_counted: 15,
  infra_excluded: 1,
  pass_rate: passedRate,
  cost: {
    n: 15,
    mean: 0.021,
    median: 0.019,
    std: 0.008,
    ci_low: 0.017,
    ci_high: 0.025,
  },
  steps: {
    n: 15,
    mean: 7.2,
    median: 7,
    std: 2.1,
    ci_low: 6.1,
    ci_high: 8.3,
  },
  tool_calls: {
    n: 15,
    mean: 9,
    median: 8,
    std: 3,
    ci_low: 7.5,
    ci_high: 10.6,
  },
  duration: {
    n: 15,
    mean: 41,
    median: 38,
    std: 12,
    ci_low: 35,
    ci_high: 47.5,
  },
  cost_confidence: { verified: 15, estimated: 0 },
  ...overrides,
})

const makeBenchmark = (
  state: Benchmark['state'],
  progress: Benchmark['progress'],
  spend_usd = 0.315,
): Benchmark => ({
  benchmark_id: benchmarkId,
  name: 'Python repair · baseline',
  state,
  config: {
    name: 'Python repair · baseline',
    agent_ids: ['agent-a-plain', 'agent-b-tools'],
    task_ids: ['fix-off-by-one'],
    scenarios: ['baseline'],
    n_runs: 3,
    spend_cap_usd: 5,
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
    payload: { passed: true, suites: 2 },
    latency: null,
    error: null,
  },
]

const agentBResult = makeResult('agent-b-tools', {
  pass_rate: {
    passed: 10,
    n: 15,
    value: 0.667,
    ci_low: 0.41,
    ci_high: 0.85,
  },
  cost: {
    n: 15,
    mean: 0.018,
    median: 0.016,
    std: 0.007,
    ci_low: 0.014,
    ci_high: 0.022,
  },
  steps: {
    n: 15,
    mean: 6.4,
    median: 6,
    std: 1.8,
    ci_low: 5.4,
    ci_high: 7.4,
  },
})

const completed = makeBenchmark('completed', {
  total: 30,
  queued: 0,
  running: 0,
  done: 29,
  infra_error: 1,
  excluded: 0,
})

const faultRun: RunDetail = {
  ...baseRun,
  status: 'FAIL',
  passed: false,
  scenario: 'provider_503_outage',
  error: 'Injected provider outage returned HTTP 503.',
}

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
    latency: 4,
    error: 'injected',
  },
]

export const agents: Agent[] = [
  {
    agent_id: 'agent-a-plain',
    name: 'Plain agent',
    mode: 'prompted',
    entrypoint: 'agents/plain/main.py',
    model_config: { model: 'mock-model' },
    description: 'A minimal agent using the OpenAI-compatible proxy.',
  },
  {
    agent_id: 'agent-b-tools',
    name: 'Tool-using agent',
    mode: 'framework',
    entrypoint: 'agents/tools/main.py',
    model_config: { model: 'mock-model' },
    description: 'A tool-using agent with a test-and-repair loop.',
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
  success: {
    label: 'Completed benchmark',
    benchmark: completed,
    results: [makeResult('agent-a-plain'), agentBResult],
    runs: [baseRun],
    events: baseEvents,
  },
  empty: {
    label: 'No benchmarks',
    benchmark: null,
    results: [],
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
    }),
    results: [
      makeResult('agent-a-plain', {
        runs_counted: 1,
        infra_excluded: 1,
        pass_rate: {
          passed: 1,
          n: 1,
          value: 1,
          ci_low: 0.21,
          ci_high: 1,
        },
        cost_confidence: { verified: 1, estimated: 0 },
      }),
    ],
    runs: [{ ...baseRun, status: 'INFRA_ERROR', passed: null, error: 'Runner could not start.' }],
    events: baseEvents,
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
    }),
    results: [
      makeResult('agent-a-plain', {
        scenario: 'provider_503_outage',
        runs_counted: 1,
        infra_excluded: 0,
        pass_rate: {
          passed: 0,
          n: 1,
          value: 0,
          ci_low: 0,
          ci_high: 0.79,
        },
      }),
    ],
    runs: [faultRun],
    events: faultEvents,
  },
  partial: {
    label: 'Results in progress',
    benchmark: makeBenchmark('running', {
      total: 30,
      queued: 12,
      running: 2,
      done: 15,
      infra_error: 1,
      excluded: 0,
    }),
    results: [makeResult('agent-a-plain')],
    runs: [baseRun],
    events: baseEvents,
  },
  halted: {
    label: 'Stopped at spend cap',
    benchmark: makeBenchmark('halted_spend_cap', {
      total: 30,
      queued: 0,
      running: 0,
      done: 8,
      infra_error: 1,
      excluded: 0,
    }, 5),
    results: [makeResult('agent-a-plain')],
    runs: [baseRun],
    events: baseEvents,
  },
}
