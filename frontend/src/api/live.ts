// Live-mode data loader (C5). Builds the same DashboardFixture shape the mock fixtures use, from the
// real API (docs/08 section 3), so every screen renders identically in mock and live mode.
// Statistics are never computed here: only server numbers are shown (TRD section 2).
import type {
  Agent,
  Benchmark,
  BenchmarkConfig,
  Event,
  Page,
  ResilienceRow,
  ResultRow,
  ResultsResponse,
  Run,
  RunDetail,
  Scenario,
  TaskSummary,
} from '../types'
import type { DashboardFixture } from '../mocks/fixtures'

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? 'http://localhost:8000'

export class ApiFailure extends Error {
  status: number
  fields: Record<string, string>
  constructor(message: string, status: number, fields: Record<string, string> = {}) {
    super(message)
    this.status = status
    this.fields = fields
  }
}

async function failureFrom(res: Response): Promise<ApiFailure> {
  let message = `API returned ${res.status}`
  let fields: Record<string, string> = {}
  try {
    const body = await res.json()
    if (body?.error?.message) message = body.error.message
    if (body?.error?.details?.fields) fields = body.error.details.fields
  } catch {
    /* keep default message */
  }
  return new ApiFailure(message, res.status, fields)
}

// POST /api/benchmarks (docs/08 section 3.2). Resolves with the queued Benchmark; rejects with ApiFailure.
export async function createBenchmark(config: BenchmarkConfig): Promise<Benchmark> {
  let res: Response
  try {
    res = await fetch(`${BASE}/api/benchmarks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
  } catch {
    throw new ApiFailure(`Cannot reach the API at ${BASE}. Is it running (docker compose up -d api)?`, 0)
  }
  if (!res.ok) throw await failureFrom(res)
  return res.json() as Promise<Benchmark>
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { signal })
  } catch {
    throw new ApiFailure(`Cannot reach the API at ${BASE}. Is it running (docker compose up -d api)?`, 0)
  }
  if (!res.ok) {
    throw await failureFrom(res)
  }
  return res.json() as Promise<T>
}

/** Benchmark shown when none is selected: the largest finished matrix (agents x tasks), so the
 *  first view is the main leaderboard rather than whatever ran last; newest wins ties. Falls back to
 *  the newest benchmark when nothing has finished. `benchmarks` arrives newest first. */
export function pickDefaultBenchmark(benchmarks: Benchmark[]): Benchmark | null {
  const finished = benchmarks.filter((b) => b.state === 'completed' || b.state === 'halted_spend_cap')
  const size = (b: Benchmark) => (b.config?.agent_ids?.length ?? 0) * (b.config?.task_ids?.length ?? 0)
  const best = finished.reduce<Benchmark | null>((top, b) => (top === null || size(b) > size(top) ? b : top), null)
  return best ?? benchmarks[0] ?? null
}

export type LiveData = {
  fixture: DashboardFixture
  benchmarks: Benchmark[]
  scenarios: Scenario[]
}

export async function loadLive(
  benchmarkId: string | null,
  runId: string | null,
  signal?: AbortSignal,
): Promise<LiveData> {
  const [benchmarkPage, agents, tasks, scenarios] = await Promise.all([
    get<Page<Benchmark>>('/api/benchmarks?limit=50', signal),
    get<Page<Agent>>('/api/agents?limit=200', signal),
    get<Page<TaskSummary>>('/api/tasks?limit=200', signal),
    get<Page<Scenario>>('/api/scenarios?limit=200', signal),
  ])
  const benchmarks = benchmarkPage.items
  const benchmark = benchmarks.find((b) => b.benchmark_id === benchmarkId) ?? pickDefaultBenchmark(benchmarks)

  let results: ResultRow[] = []
  let compareResults: ResultRow[] = []
  let resilience: ResilienceRow[] = []
  let runs: RunDetail[] = []
  let events: Event[] = []
  let generatedAt: string | undefined

  if (benchmark) {
    const id = benchmark.benchmark_id
    const [byAgent, byAgentTask, resil, runPage] = await Promise.all([
      get<ResultsResponse>(`/api/benchmarks/${id}/results?group_by=agent`, signal),
      get<ResultsResponse>(`/api/benchmarks/${id}/results?group_by=agent_task`, signal),
      get<{ items: ResilienceRow[] }>(`/api/benchmarks/${id}/resilience`, signal),
      get<Page<Run>>(`/api/runs?benchmark_id=${id}&limit=200`, signal),
    ])
    results = byAgent.items
    generatedAt = byAgent.generated_at
    compareResults = byAgentTask.items
    resilience = resil.items
    runs = runPage.items.map((r) => ({ ...r, env_fingerprint: null, grader_result: null, workspace_diff: null }))
  }

  // Run detail + trace are fetched only for the run being viewed.
  if (runId) {
    const [detail, ev] = await Promise.all([
      get<RunDetail>(`/api/runs/${runId}`, signal),
      get<Page<Event>>(`/api/runs/${runId}/events?limit=1000`, signal),
    ])
    runs = runs.some((r) => r.run_id === runId)
      ? runs.map((r) => (r.run_id === runId ? detail : r))
      : [...runs, detail]
    events = ev.items
  }

  return {
    benchmarks,
    scenarios: scenarios.items,
    fixture: {
      label: 'Live API',
      generatedAt,
      benchmark,
      resilience,
      catalog: { agents: agents.items, tasks: tasks.items },
      results,
      compareResults,
      runs,
      events,
    },
  }
}
