// Live-mode data loader (C5). Builds the same DashboardFixture shape the mock fixtures use, from the
// real API (docs/08 section 3), so every screen renders identically in mock and live mode.
// Statistics are never computed here: only server numbers are shown (TRD section 2).
import type {
  Agent,
  Benchmark,
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
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, { signal })
  } catch {
    throw new ApiFailure(`Cannot reach the API at ${BASE}. Is it running (docker compose up -d api)?`, 0)
  }
  if (!res.ok) {
    let message = `API returned ${res.status}`
    try {
      const body = await res.json()
      if (body?.error?.message) message = body.error.message
    } catch {
      /* keep default message */
    }
    throw new ApiFailure(message, res.status)
  }
  return res.json() as Promise<T>
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
  const benchmark = benchmarks.find((b) => b.benchmark_id === benchmarkId) ?? benchmarks[0] ?? null

  let results: ResultRow[] = []
  let compareResults: ResultRow[] = []
  let resilience: ResilienceRow[] = []
  let runs: RunDetail[] = []
  let events: Event[] = []

  if (benchmark) {
    const id = benchmark.benchmark_id
    const [byAgent, byAgentTask, resil, runPage] = await Promise.all([
      get<ResultsResponse>(`/api/benchmarks/${id}/results?group_by=agent`, signal),
      get<ResultsResponse>(`/api/benchmarks/${id}/results?group_by=agent_task`, signal),
      get<{ items: ResilienceRow[] }>(`/api/benchmarks/${id}/resilience`, signal),
      get<Page<Run>>(`/api/runs?benchmark_id=${id}&limit=200`, signal),
    ])
    results = byAgent.items
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
