import http from "k6/http";
import { check, sleep } from "k6";

const target = __ENV.TARGET_URL || "http://host.docker.internal:8000";
const loadTestToken = __ENV.LOAD_TEST_TOKEN || "phase7-local-load-test";
const runId = __ENV.LOAD_TEST_RUN_ID || "phase7-local";

export const options = {
  stages: [
    { duration: "10s", target: 5 },
    { duration: "30s", target: 5 },
    { duration: "10s", target: 0 },
  ],
  summaryTrendStats: ["avg", "min", "med", "p(90)", "p(95)", "p(99)", "max"],
  thresholds: {
    checks: ["rate>0.99"],
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500", "p(99)<1000"],
  },
  tags: {
    traffic_class: "load_test",
    suite: "phase7-light",
  },
};

function headers() {
  return {
    "Content-Type": "application/json",
    "X-Guest-ID": `${runId}-vu-${__VU}`,
    "X-Request-ID": `${runId}-${__VU}-${__ITER}`,
    "X-AutoMind-Traffic-Class": "load_test",
    "X-Load-Test-Token": loadTestToken,
  };
}

export default function () {
  const selector = __ITER % 5;
  let response;

  if (selector === 0) {
    const message = __ITER % 10 === 0 ? "我有点冷" : "电量还有多少";
    response = http.post(
      `${target}/api/v1/chat`,
      JSON.stringify({ message }),
      { headers: headers(), tags: { endpoint: "chat" } },
    );
  } else if (selector === 1) {
    response = http.get(`${target}/health`, {
      headers: headers(),
      tags: { endpoint: "health" },
    });
  } else {
    response = http.get(`${target}/api/v1/vehicle/state`, {
      headers: headers(),
      tags: { endpoint: "vehicle-state" },
    });
  }

  check(response, {
    "status is 200": (result) => result.status === 200,
    "request id returned": (result) => Boolean(result.headers["X-Request-Id"]),
    "trace id returned": (result) => Boolean(result.headers["X-Trace-Id"]),
  });
  sleep(0.5);
}

export function handleSummary(data) {
  const duration = data.metrics.http_req_duration?.values || {};
  const failed = data.metrics.http_req_failed?.values || {};
  const checks = data.metrics.checks?.values || {};
  const iterations = data.metrics.iterations?.values || {};
  const line = [
    `iterations=${iterations.count || 0}`,
    `p50_ms=${duration.med || 0}`,
    `p95_ms=${duration["p(95)"] || 0}`,
    `p99_ms=${duration["p(99)"] || 0}`,
    `error_rate=${failed.rate || 0}`,
    `check_rate=${checks.rate || 0}`,
  ].join(" ");
  return {
    "results/latest-summary.json": JSON.stringify(data, null, 2),
    stdout: `${line}\n`,
  };
}
