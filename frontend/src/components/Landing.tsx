import { useEffect, useState } from 'react'
import './Landing.css'

/** Public landing page (/home). Every number below comes from the frozen demo data in db/demo-data.sql (X6, 15 Nov 2026). */

const dashboardHref = '/?mode=live'

const tabs = [
  { id: 'leaderboard', label: 'Leaderboard', blurb: 'Pass rate with 95% intervals, cost, steps and time, side by side.' },
  { id: 'faults', label: 'Failure scenarios', blurb: 'Break the provider or a tool on purpose and watch who recovers.' },
  { id: 'trace', label: 'Run timeline', blurb: 'Every LLM call and tool call, in order, with tokens and cost.' },
  { id: 'grading', label: 'Grading', blurb: 'Visible and hidden tests on a clean copy, with tamper checks.' },
] as const

type TabId = (typeof tabs)[number]['id']

export default function Landing() {
  const [tab, setTab] = useState<TabId>('leaderboard')
  const active = tabs.find((t) => t.id === tab)!

  // Scroll reveal + highlight sweep: one observer, adds .is-in once.
  useEffect(() => {
    const els = document.querySelectorAll('.lp-reveal, .lp-hl')
    if (!('IntersectionObserver' in window)) { els.forEach((e) => e.classList.add('is-in')); return }
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add('is-in'); io.unobserve(e.target) }
    }), { threshold: 0.35 })
    els.forEach((e) => io.observe(e))
    return () => io.disconnect()
  }, [])

  return (
    <div className="lp">
      <header className="lp-nav">
        <a className="lp-brand" href="/home">
          <span className="lp-mark" aria-hidden="true">A</span>AgentArena
        </a>
        <nav aria-label="Landing">
          <a href="#how">How it works</a>
          <a href="#product">Product</a>
          <a href="#results">Results</a>
          <a href="https://github.com/yokshith09/AgentArena">GitHub</a>
        </nav>
        <a className="lp-btn lp-btn-dark" href={dashboardHref}>Open dashboard</a>
      </header>

      <main>
        <section className="lp-hero">
          <div className="lp-hero-copy">
          <p className="lp-eyebrow">Agent benchmarking · Bifrost gateway</p>
          <h1>Benchmark the agent,<br />not just the model.</h1>
          <p className="lp-lede">
            Run any agent as a black box on identical tasks. Every LLM call is measured through Bifrost, every
            result is graded with hidden tests, and every number comes with a confidence interval.
          </p>
          <div className="lp-actions">
            <a className="lp-btn lp-btn-dark" href={dashboardHref}>Explore the results</a>
            <a className="lp-btn lp-btn-line" href="#how">See how it works</a>
          </div>
          </div>
          <HeroChart />
          <dl className="lp-stats lp-reveal">
            <div><dt>Real runs</dt><dd>33</dd></div>
            <div><dt>Infra errors</dt><dd>0</dd></div>
            <div><dt>Total spend</dt><dd>$0.011</dd></div>
            <div><dt>Proxy overhead</dt><dd>+17 ms</dd></div>
          </dl>
        </section>

        <section className="lp-section" id="how" aria-labelledby="how-title">
          <p className="lp-eyebrow">How it works</p>
          <h2 id="how-title">Plug in any agent. No code changes.</h2>
          <p className="lp-sub">
            Point the agent's <code>OPENAI_BASE_URL</code> at AgentArena. Every call flows through the measuring
            proxy and Bifrost, so <mark className="lp-hl">the agent never knows it is being measured</mark>.
          </p>
          <div className="lp-flow lp-reveal">
            <div className="lp-box">
              <h3>Your agents</h3>
              <p>Any program that speaks the OpenAI API</p>
              <ul className="lp-list">
                <li><b>Agent A</b> framework-free loop</li>
                <li><b>Agent B</b> OpenAI Agents SDK</li>
                <li><b>Agent C</b> loop with retry on 429 / 5xx</li>
              </ul>
            </div>
            <div className="lp-arrow" aria-hidden="true" />
            <div className="lp-stack">
              <div className="lp-box">
                <h3>Measuring proxy</h3>
                <p>Tokens, cost, latency and tool calls for every request. Injects 503 and 429 faults on demand.</p>
              </div>
              <div className="lp-box">
                <h3>Bifrost gateway</h3>
                <p>The single route to Groq <code>gpt-oss-20b</code>. Provider keys live only here.</p>
              </div>
            </div>
            <div className="lp-arrow" aria-hidden="true" />
            <div className="lp-box lp-box-main">
              <h3><span className="lp-mark lp-mark-sm" aria-hidden="true">A</span>AgentArena</h3>
              <p className="lp-label">measure</p>
              <div className="lp-chips"><span>Traces</span><span>Cost</span><span>Latency</span></div>
              <p className="lp-label">stress</p>
              <div className="lp-chips"><span>Outage</span><span>Rate limit</span><span>Broken tool</span><span>Bad hint</span></div>
              <p className="lp-label">judge</p>
              <div className="lp-chips"><span>Hidden tests</span><span>Tamper checks</span><span>95% intervals</span></div>
              <div className="lp-via">
                <span className="lp-label">every result via</span>
                <div className="lp-chips lp-chips-dark"><span>Dashboard</span><span>REST API</span><span>CLI</span></div>
              </div>
            </div>
          </div>
        </section>

        <section className="lp-section" id="product" aria-labelledby="product-title">
          <p className="lp-eyebrow">Product</p>
          <h2 id="product-title">From leaderboard to a single LLM call.</h2>
          <div className="lp-showcase lp-reveal">
            <div className="lp-tabs" role="tablist" aria-label="Product views">
              {tabs.map((t) => (
                <button
                  key={t.id}
                  role="tab"
                  id={`tab-${t.id}`}
                  aria-selected={tab === t.id}
                  aria-controls="lp-panel"
                  tabIndex={tab === t.id ? 0 : -1}
                  onClick={() => setTab(t.id)}
                  onKeyDown={(event) => {
                    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return
                    const i = tabs.findIndex((x) => x.id === tab)
                    const next = tabs[(i + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length]
                    setTab(next.id)
                    document.getElementById(`tab-${next.id}`)?.focus()
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <p className="lp-blurb" key={tab}>{active.blurb}</p>
            <div className="lp-window" id="lp-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
              <div className="lp-window-bar"><span /><span /><span /><b>{active.label}</b></div>
              {tab === 'leaderboard' && <LeaderboardPreview />}
              {tab === 'faults' && <FaultPreview />}
              {tab === 'trace' && <TracePreview />}
              {tab === 'grading' && <GradingPreview />}
            </div>
          </div>
        </section>

        <section className="lp-section" id="results" aria-labelledby="results-title">
          <p className="lp-eyebrow">Results</p>
          <h2 id="results-title">Same model. Different agents. Different outcomes.</h2>
          <div className="lp-grid3 lp-reveal">
            <article className="lp-box">
              <p className="lp-label">baseline</p>
              <h3>Agent B passed 5 of 5</h3>
              <p>Agents A and C passed 4 of 5. Both missed a hidden test on <code>fix-off-by-one</code> that the visible tests did not catch.</p>
            </article>
            <article className="lp-box">
              <p className="lp-label">under faults</p>
              <h3>Retry logic matters</h3>
              <p>Agent A failed under the outage, rate-limit and tool faults. Agent C was the only agent to survive the 429 rate limit.</p>
            </article>
            <article className="lp-box">
              <p className="lp-label">measurement</p>
              <h3>Tokens match Bifrost exactly</h3>
              <p>Proxy token counts matched Bifrost's own logs. The proxy adds a median of 17.3 ms per call.</p>
            </article>
          </div>
          <p className="lp-note">
            One run per cell on the Groq free tier, so intervals are wide: <mark className="lp-hl">these results demonstrate the method, not a final ranking</mark>.
          </p>
        </section>

        <section className="lp-cta">
          <h2>See every run behind every number.</h2>
          <div className="lp-actions">
            <a className="lp-btn lp-btn-light" href={dashboardHref}>Open the dashboard</a>
            <a className="lp-btn lp-btn-ghost" href="/benchmarks/new">Launch a benchmark</a>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <span>AgentArena · Global AI Hackathon · Problem Statement 02</span>
        <span>Built on Bifrost by Maxim AI</span>
      </footer>
    </div>
  )
}

/** Pass rate with Wilson 95% intervals, X6 baseline (5 tasks per agent). */
function HeroChart() {
  const rows = [
    { name: 'Agent B', sub: 'Agents SDK', k: 5, lo: 0.566, hi: 1 },
    { name: 'Agent A', sub: 'plain loop', k: 4, lo: 0.376, hi: 0.964 },
    { name: 'Agent C', sub: 'retry loop', k: 4, lo: 0.376, hi: 0.964 },
  ]
  const [hover, setHover] = useState<number | null>(null)
  const x = (v: number) => 120 + v * 300
  return (
    <figure className="lp-chart" aria-labelledby="lp-chart-cap">
      <div className="lp-chart-head">
        <span>Pass rate, 95% interval</span>
        <span className="lp-live"><i />X6 baseline</span>
      </div>
      <svg viewBox="0 0 440 230" role="img" aria-label="Agent B passed 5 of 5; Agents A and C passed 4 of 5. Intervals overlap.">
        <defs>
          <linearGradient id="lp-ci" x1="0" x2="1"><stop offset="0" stopColor="var(--lp-a)" /><stop offset="1" stopColor="var(--lp-b)" /></linearGradient>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1="14" y2="190" className="lp-grid-line" />
            <text x={x(t)} y="210" textAnchor="middle" className="lp-axis">{t * 100}%</text>
          </g>
        ))}
        {rows.map((r, i) => {
          const y = 46 + i * 56
          return (
            <g key={r.name} className={`lp-ci-row${hover === i ? ' is-hot' : ''}${hover !== null && hover !== i ? ' is-dim' : ''}`}
              onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} style={{ ['--d' as string]: `${i * 140}ms` }}>
              <rect x="0" y={y - 24} width="440" height="48" fill="transparent" />
              <text x="0" y={y - 2} className="lp-ci-name">{r.name}</text>
              <text x="0" y={y + 14} className="lp-axis">{r.sub}</text>
              <rect x={x(r.lo)} y={y - 5} width={x(r.hi) - x(r.lo)} height="10" rx="5" fill="url(#lp-ci)" className="lp-ci-bar" />
              <circle cx={x(r.k / 5)} cy={y} r="7" className="lp-ci-dot" />
              {hover === i && <text x={x(r.k / 5)} y={y - 14} textAnchor="middle" className="lp-ci-tip">{r.k}/5 · {Math.round(r.lo * 100)}–{Math.round(r.hi * 100)}%</text>}
            </g>
          )
        })}
      </svg>
      <figcaption id="lp-chart-cap">Overlapping intervals: with five tasks, no agent is a clear winner yet.</figcaption>
    </figure>
  )
}

function LeaderboardPreview() {
  const rows = [
    { name: 'Agent B · OpenAI Agents SDK', passed: 5 },
    { name: 'Agent A · plain loop', passed: 4 },
    { name: 'Agent C · retry loop', passed: 4 },
  ]
  return (
    <div className="lp-preview">
      <p className="lp-label">X6 final · baseline · 5 tasks</p>
      {rows.map((r) => (
        <div className="lp-bar-row" key={r.name}>
          <span>{r.name}</span>
          <span className="lp-bar"><i style={{ width: `${(r.passed / 5) * 100}%` }} /></span>
          <b>{r.passed}/5</b>
        </div>
      ))}
    </div>
  )
}

function FaultPreview() {
  const cells: [string, string, string, string][] = [
    ['Agent A', 'fail', 'fail', 'fail'],
  ]
  return (
    <div className="lp-preview">
      <p className="lp-label">X6 final · faults · Agent A, one run per fault</p>
      <table className="lp-table">
        <thead><tr><th scope="col">Agent</th><th scope="col">503 outage</th><th scope="col">429 rate limit</th><th scope="col">Tool error</th></tr></thead>
        <tbody>
          {cells.map(([agent, ...results]) => (
            <tr key={agent}><th scope="row">{agent}</th>{results.map((r, i) => <td key={i}><span className={`lp-pill lp-${r}`}>{r.toUpperCase()}</span></td>)}</tr>
          ))}
        </tbody>
      </table>
      <p className="lp-small">Agent C, with code-level retry, was the only agent to pass under the 429 rate limit.</p>
    </div>
  )
}

function TracePreview() {
  const steps = [
    ['llm_call', 'Model asks to read the workspace'],
    ['tool_call', 'list_files · read_file solution.py'],
    ['llm_call', 'Model proposes a fix'],
    ['tool_call', 'write_file solution.py'],
    ['tool_call', 'run_tests'],
    ['grader', 'visible + hidden suites'],
  ]
  return (
    <ol className="lp-preview lp-trace">
      {steps.map(([kind, text], i) => (
        <li key={i}><span className={`lp-kind lp-kind-${kind}`}>{kind}</span>{text}</li>
      ))}
      <li className="lp-small">Illustrative order of events; each recorded event carries tokens, cost and latency.</li>
    </ol>
  )
}

function GradingPreview() {
  const checks = [
    'Grades a clean copy of the workspace',
    'Restores protected test files before grading',
    'Runs hidden tests the agent never saw',
    'Flags edited or deleted tests and planted conftest.py',
    'Treats zero collected tests as a failure',
  ]
  return (
    <ul className="lp-preview lp-checks">
      {checks.map((c) => <li key={c}>{c}</li>)}
    </ul>
  )
}
