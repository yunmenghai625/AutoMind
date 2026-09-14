# Phase 7 k6 Light Load Test

This suite is synthetic test traffic, not evidence of real users. It keeps Safety and Redis rate limiting
enabled and labels requests as `load_test` only when the API validates `X-Load-Test-Token`.

Start the API with `LOAD_TEST_TOKEN` configured, then run:

```powershell
docker run --rm `
  -e TARGET_URL=http://host.docker.internal:8000 `
  -e LOAD_TEST_TOKEN=replace-with-the-configured-token `
  -e LOAD_TEST_RUN_ID=phase7-local `
  -v "${PWD}/loadtests:/scripts" `
  -w /scripts `
  grafana/k6:latest run k6-smoke.js
```

The test ramps to five virtual users, holds for 30 seconds, and calls health, vehicle-state and a
deterministic read-only Agent scenario. Each virtual user has a distinct Guest ID so the configured
production rate limiter remains active without accidental shared-identity throttling. Thresholds require
less than 1% HTTP failures, more than 99% successful checks, P95 below 500 ms and P99 below 1000 ms.

The raw result is written to `loadtests/results/latest-summary.json` and is intentionally ignored by Git.
Record the environment, timestamp and selected values in `docs/phase-7-load-test-report.md`.
