export type ApiError = {
  error: {
    code: 'NOT_FOUND' | 'VALIDATION_ERROR' | 'CONFLICT' | 'INTERNAL'
    message: string
    details: Record<string, unknown> | null
  }
}

export type Page<T> = {
  items: T[]
  total: number
}

export type Agent = {
  agent_id: string
  name: string
  mode: string
  entrypoint: string
  model_config: Record<string, unknown>
  description: string | null
}

export type TaskSummary = {
  task_id: string
  category: string
  prompt: string
  grader_type: string
  faults_allowed: string[]
  validated: boolean
  weak: boolean | null
}

export type Scenario = {
  id: string
  group: 'baseline' | 'provider' | 'tool' | 'instruction' | 'environment'
  layer: 'none' | 'proxy' | 'agent_env' | 'runner'
  description: string
}

export type BenchmarkConfig = {
  name: string
  agent_ids: string[]
  task_ids: string[]
  scenarios: string[]
  n_runs: number
  spend_cap_usd: number
}

export type Benchmark = {
  benchmark_id: string
  name: string
  state: 'queued' | 'running' | 'completed' | 'halted_spend_cap' | 'failed'
  config: BenchmarkConfig
  progress: {
    total: number
    queued: number
    running: number
    done: number
    infra_error: number
    excluded: number
  }
  spend_usd: number
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export type PassRate = {
  passed: number
  n: number
  value: number | null
  ci_low: number | null
  ci_high: number | null
}

export type Stat = {
  n: number
  mean: number | null
  median: number | null
  std: number | null
  ci_low: number | null
  ci_high: number | null
}

export type ResultRow = {
  agent_id: string
  task_id: string | null
  scenario: string
  runs_counted: number
  infra_excluded: number
  pass_rate: PassRate
  cost: Stat
  steps: Stat
  tool_calls: Stat
  duration: Stat
  cost_confidence: {
    verified: number
    estimated: number
  }
}

export type ResultsResponse = {
  items: ResultRow[]
  benchmark_id: string
  generated_at: string
}

export type Run = {
  run_id: string
  benchmark_id: string | null
  agent_id: string
  task_id: string
  scenario: string
  repeat_index: number
  attempt: number
  state: string
  status: 'PASS' | 'FAIL' | 'INFRA_ERROR' | null
  passed: boolean | null
  model: string | null
  tokens_in: number | null
  tokens_out: number | null
  cost: number | null
  cost_confidence: 'verified' | 'estimated' | null
  duration: number | null
  steps: number | null
  tool_calls: number | null
  started_at: string | null
  finished_at: string | null
  error: string | null
}

export type GradeResult = {
  passed: boolean
  tamper_detected: boolean
  suites: Array<{
    name: 'visible' | 'hidden'
    passed: boolean
    tests_total: number
    tests_failed: number
  }>
  summary: string
  error: string | null
}

export type RunDetail = Run & {
  env_fingerprint: Record<string, unknown> | null
  grader_result: GradeResult | null
  workspace_diff: string | null
}

export type Event = {
  id: number
  run_id: string
  ts: string
  type: string
  agent_role: string | null
  payload: Record<string, unknown>
  latency: number | null
  error: string | null
}

export type ResilienceRow = {
  agent_id: string
  scenario: string
  baseline_pass_rate: PassRate
  scenario_pass_rate: PassRate
  resilience_score: number | null
}
