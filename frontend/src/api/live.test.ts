import { describe, expect, it } from 'vitest'
import { pickDefaultBenchmark } from './live'
import type { Benchmark } from '../types'

function bench(id: string, state: Benchmark['state'], agents: number, tasks: number): Benchmark {
  return {
    benchmark_id: id,
    name: id,
    state,
    config: {
      name: id,
      agent_ids: Array.from({ length: agents }, (_, i) => `a${i}`),
      task_ids: Array.from({ length: tasks }, (_, i) => `t${i}`),
      scenarios: ['baseline'],
      n_runs: 1,
      spend_cap_usd: 1,
    },
    progress: { total: 0, queued: 0, running: 0, done: 0, infra_error: 0, excluded: 0 },
    spend_usd: 0,
    error: null,
    created_at: '2026-11-15T00:00:00Z',
    started_at: null,
    finished_at: null,
  }
}

describe('pickDefaultBenchmark', () => {
  it('prefers the largest finished matrix over the newest benchmark', () => {
    // API order is newest first: a small faults run, then the main 3 x 5 baseline.
    const list = [bench('faults', 'completed', 3, 1), bench('baseline', 'completed', 3, 5), bench('pilot', 'completed', 2, 1)]
    expect(pickDefaultBenchmark(list)?.benchmark_id).toBe('baseline')
  })

  it('ignores unfinished benchmarks and keeps the newest on ties', () => {
    const list = [bench('running-big', 'running', 5, 5), bench('newer', 'completed', 2, 2), bench('older', 'completed', 2, 2)]
    expect(pickDefaultBenchmark(list)?.benchmark_id).toBe('newer')
  })

  it('falls back to the newest when nothing has finished, and to null when empty', () => {
    expect(pickDefaultBenchmark([bench('q', 'queued', 1, 1)])?.benchmark_id).toBe('q')
    expect(pickDefaultBenchmark([])).toBeNull()
  })
})
