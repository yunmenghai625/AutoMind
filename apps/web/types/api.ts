/**
 * API Service Layer types & shared helpers.
 *
 * Every real network call goes through lib/api/*. In mock mode these
 * services resolve from lib/mock/*; in live mode they hit the FastAPI
 * backend. Components never call fetch() directly.
 */

export interface ApiError {
  status: number;
  code: string;
  message: string;
}

export type AsyncResult<T> =
  | { status: "success"; data: T }
  | { status: "error"; error: ApiError };

// Future backend contract paths (documented here for the backend team):
//
//   GET  /api/v1/vehicle/state
//   POST /api/v1/vehicle/control
//   POST /api/v1/chat
//   POST /api/v1/knowledge/query
//   POST /api/v1/diagnosis
//   GET  /api/v1/garage/vehicle
//   GET  /api/v1/vehicle/recalls
//   GET  /api/v1/admin/overview
//   GET  /api/v1/admin/metrics
//   GET  /api/v1/admin/agent-runs
//   GET  /api/v1/admin/agent-runs/{id}
