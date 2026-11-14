// Dumps frontend mock fixtures as JSON for tests/contracts/test_fixtures_vs_api_models.py (X4 / T-30).
import { mockFixtures } from '../../frontend/src/mocks/fixtures.ts'
console.log(JSON.stringify(mockFixtures))
