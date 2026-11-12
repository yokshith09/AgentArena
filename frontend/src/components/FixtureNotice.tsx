import type { DashboardFixture, FixtureState } from '../mocks/fixtures'

export default function FixtureNotice({
  fixture,
  state,
}: {
  fixture: DashboardFixture
  state: FixtureState
}) {
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
