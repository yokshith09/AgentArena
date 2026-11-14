// Dashboard regression tests (T-17 automated). Mock mode renders every route in every fixture state;
// live mode is exercised against a stubbed fetch that returns docs/08-shaped API payloads.
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { mockFixtures, scenarios } from './mocks/fixtures'

const ROUTES = ['/', '/benchmarks', '/benchmarks/new', '/compare', '/runs', '/resilience', '/catalog', '/security', '/limitations']
const STATES = ['success', 'empty', 'infra', 'fault', 'partial', 'halted', 'loading', 'error'] as const
const fx = mockFixtures.success

function visit(path: string) {
  window.history.pushState({}, '', path)
}

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))
}

const GENERATED_AT = '2026-11-14T10:00:00Z'

/** Routes API paths to docs/08-shaped payloads built from the success fixture. */
function stubApi(overrides: Record<string, (init?: RequestInit) => Promise<Response>> = {}) {
  const handlers: Record<string, (init?: RequestInit) => Promise<Response>> = {
    '/api/benchmarks?': () => json({ items: [fx.benchmark], total: 1 }),
    '/api/agents': () => json({ items: fx.catalog.agents, total: fx.catalog.agents.length }),
    '/api/tasks': () => json({ items: fx.catalog.tasks, total: fx.catalog.tasks.length }),
    '/api/scenarios': () => json({ items: scenarios, total: scenarios.length }),
    'group_by=agent_task': () => json({ items: fx.compareResults, benchmark_id: 'b', generated_at: GENERATED_AT }),
    'group_by=agent': () => json({ items: fx.results, benchmark_id: 'b', generated_at: GENERATED_AT }),
    '/resilience': () => json({ items: fx.resilience }),
    '/api/runs?': () => json({ items: fx.runs, total: fx.runs.length }),
    ...overrides,
  }
  const fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const key = Object.keys(handlers).find((k) => url.includes(k))
    return key ? handlers[key](init) : json({ error: { code: 'NOT_FOUND', message: `no stub for ${url}`, details: null } }, 404)
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

beforeEach(() => {
  vi.spyOn(console, 'error').mockImplementation(() => {}) // jsdom: "navigation not implemented"
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('mock mode', () => {
  for (const route of ROUTES) {
    it(`renders ${route} in every fixture state with the MOCK ribbon`, () => {
      for (const state of STATES) {
        visit(`${route}?state=${state}`)
        const { container, unmount } = render(<App />)
        expect(container.querySelector('main'), `${route} ${state}`).not.toBeNull()
        expect(screen.getByText(/MOCK DATA/)).toBeTruthy()
        unmount()
      }
    })
  }
})

describe('live mode', () => {
  it('renders API data, labels it LIVE, and shows the API generation time', async () => {
    stubApi()
    visit('/?mode=live')
    render(<App />)
    await waitFor(() => expect(screen.getByText(/LIVE — data from the AgentArena API/)).toBeTruthy())
    await waitFor(() => expect(screen.getAllByText(fx.catalog.agents[0].name).length).toBeGreaterThan(0))
    expect(screen.queryByText(/MOCK DATA/)).toBeNull()
    expect(document.body.textContent).not.toContain('Jan 1, 2026')
    expect(document.body.textContent).toContain(new Date(GENERATED_AT).toLocaleString())
  })

  it('says the API is unreachable (not "simulated fixture") when the API is down', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('failed to fetch'))))
    visit('/?mode=live')
    render(<App />)
    await waitFor(() => expect(screen.getByText(/Cannot reach the API/)).toBeTruthy())
    expect(screen.getByRole('button', { name: 'Retry' })).toBeTruthy()
    expect(document.body.textContent).not.toContain('simulated fixture')
    expect(screen.getByText('LIVE API UNAVAILABLE')).toBeTruthy()
  })

  it('keeps live mode when navigating with header links', async () => {
    stubApi()
    visit('/?mode=live')
    render(<App />)
    await waitFor(() => expect(screen.getByText(/LIVE — data from/)).toBeTruthy())
    const nav = screen.getByRole('navigation', { name: 'Primary navigation' })
    const hrefs = Array.from(nav.querySelectorAll('a')).map((a) => a.getAttribute('href'))
    expect(hrefs.length).toBeGreaterThan(4)
    for (const href of hrefs) expect(href).toContain('mode=live')
  })

  async function fillAndSubmit() {
    visit('/benchmarks/new?mode=live')
    render(<App />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Queue benchmark' })).toBeTruthy())
    fireEvent.change(screen.getByLabelText('Benchmark name'), { target: { value: 'My run' } })
    fireEvent.click(screen.getByRole('button', { name: 'Queue benchmark' }))
  }

  it('POSTs the benchmark config to /api/benchmarks', async () => {
    const queued = { ...fx.benchmark, name: 'My run', state: 'queued' }
    const fetchMock = stubApi({ '/api/benchmarks': (init) => (init?.method === 'POST' ? json(queued, 202) : json({ items: [queued], total: 1 })) })
    await fillAndSubmit()
    await waitFor(() => expect(screen.getByText(/queued/)).toBeTruthy())
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(post).toBeTruthy()
    expect(String(post![0])).toContain('/api/benchmarks')
    const body = JSON.parse(String(post![1]!.body))
    expect(body).toMatchObject({ name: 'My run', n_runs: 3, spend_cap_usd: 5, scenarios: ['baseline'] })
    expect(body.agent_ids.length).toBeGreaterThan(0)
    expect(body.task_ids.length).toBeGreaterThan(0)
  })

  it('shows server-side field errors from a 422 response', async () => {
    stubApi({
      '/api/benchmarks': (init) =>
        init?.method === 'POST'
          ? json({ error: { code: 'VALIDATION_ERROR', message: 'validation failed', details: { fields: { n_runs: 'must be 1..10 (server)' } } } }, 422)
          : json({ items: [fx.benchmark], total: 1 }),
    })
    await fillAndSubmit()
    await waitFor(() => expect(screen.getByText(/API rejected the benchmark/)).toBeTruthy())
    expect(screen.getByText('must be 1..10 (server)')).toBeTruthy()
  })
})
