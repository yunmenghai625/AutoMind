import { http, simulate } from "@/lib/api/apiClient";
import { authHeaders } from "@/lib/api/identity";
import { API_MODE } from "@/lib/config";
import {
  DEFAULT_VEHICLE_STATE,
  type VehicleControlAction,
  type VehicleState,
} from "@/types/vehicle";

/**
 * Vehicle / Digital Twin services.
 *
 * Backend contract (FastAPI Phase 1, apps/api):
 *   GET  /api/v1/vehicle/state
 *   POST /api/v1/vehicle/control
 *
 * - mock mode: resolves immediately with local data, no network.
 * - live mode: maps frontend VehicleState <-> FastAPI VehicleState
 *   (snake_case wire format), including optimistic-lock version handshake.
 */

const API_MODE_IS_LIVE = API_MODE === "live";

// ---------- wire <-> domain mapping ----------

const GEAR_MAP: Record<string, VehicleState["gear"]> = {
  P: "P",
  R: "R",
  N: "N",
  D: "D",
  B: "D", // frontend supports B (regenerative), backend does not
};

const HEADLIGHT_MAP: Record<string, VehicleState["headlight"]> = {
  OFF: "OFF",
  PARKING: "ON",
  LOW_BEAM: "ON",
  HIGH_BEAM: "ON",
};

const WINDOW_STEPS = [0, 25, 50, 75, 100] as const;

function toWindowLevel(value: number): VehicleState["windowFL"] {
  let best: number = WINDOW_STEPS[0];
  for (const step of WINDOW_STEPS) {
    if (Math.abs(value - step) < Math.abs(value - best)) best = step;
  }
  return best as VehicleState["windowFL"];
}

interface BackendVehicleState {
  speed_kph: number;
  gear: string;
  battery_soc: number;
  range_km: number;
  climate: { driver_temp_c: number; passenger_temp_c: number };
  seat_heat: { driver: number; passenger: number };
  window_position: { driver: number; passenger: number };
  light_state: string;
  charge_status: string;
  version: number;
}

function fromBackend(raw: BackendVehicleState): VehicleState {
  const climate = raw.climate ?? { driver_temp_c: 22, passenger_temp_c: 22 };
  const heated = climate.driver_temp_c !== 22 || climate.passenger_temp_c !== 22;
  return {
    speed: raw.speed_kph ?? 0,
    gear: GEAR_MAP[raw.gear] ?? "P",
    batterySoc: raw.battery_soc ?? 0,
    rangeKm: raw.range_km ?? 0,
    driverTemperature: climate.driver_temp_c ?? 22,
    passengerTemperature: climate.passenger_temp_c ?? 22,
    driverSeatHeat: (raw.seat_heat?.driver ?? 0) as VehicleState["driverSeatHeat"],
    passengerSeatHeat:
      (raw.seat_heat?.passenger ?? 0) as VehicleState["passengerSeatHeat"],
    acStatus: heated ? "ON" : "OFF",
    windowFL: toWindowLevel(raw.window_position?.driver ?? 0),
    windowFR: toWindowLevel(raw.window_position?.passenger ?? 0),
    headlight: HEADLIGHT_MAP[raw.light_state] ?? "OFF",
    chargeStatus: raw.charge_status === "CHARGING" ? "CHARGING" : "IDLE",
  };
}

interface ControlPayload {
  property: string;
  zone?: string;
  value: number | string;
}

/**
 * Translate a frontend control action into the backend control payload.
 * Returns null for actions the Phase 1 backend cannot persist
 * (AC toggle and speed are not writable on the backend yet).
 */
function toControlPayload(action: VehicleControlAction): ControlPayload | null {
  switch (action.kind) {
    case "ac":
      // No writable AC property in Phase 1 backend; never sent.
      return null;
    case "climate":
      return {
        property: action.zone === "driver" ? "DRIVER_TEMP" : "PASSENGER_TEMP",
        value: action.value,
      };
    case "seat_heat":
      return { property: "SEAT_HEAT", zone: action.zone, value: action.value };
    case "window":
      return {
        property: "WINDOW_POSITION",
        zone: action.zone === "FL" ? "driver" : "passenger",
        value: action.value,
      };
    case "headlight":
      // Backend supports OFF/PARKING/LOW_BEAM/HIGH_BEAM (no AUTO).
      return {
        property: "LIGHT_STATE",
        value: action.value === "OFF" ? "OFF" : "LOW_BEAM",
      };
    case "speed":
      // Read-only on backend (VEHICLE_SPEED).
      return null;
    default:
      return null;
  }
}

// ---------- services ----------

export async function getVehicleState(): Promise<VehicleState> {
  if (API_MODE_IS_LIVE) {
    const res = await http<{ state: BackendVehicleState }>("/api/v1/vehicle/state", {
      headers: authHeaders(),
    });
    return fromBackend(res.state);
  }
  return simulate(() => ({ ...DEFAULT_VEHICLE_STATE }));
}

/**
 * Apply a control action on the backend (live) or locally (mock).
 * Live mode performs an optimistic-lock handshake: reads the current
 * `version`, then POSTs with `expected_version`.
 *
 * Returns the authoritative vehicle state after the change, or null when
 * the action is not persisted by the Phase 1 backend.
 */
export async function controlVehicle(
  action: VehicleControlAction,
): Promise<VehicleState | null> {
  if (!API_MODE_IS_LIVE) {
    return null;
  }

  const payload = toControlPayload(action);
  if (!payload) return null;

  const current = await http<{ state: { version: number } }>(
    "/api/v1/vehicle/state",
    { headers: authHeaders() },
  );
  const res = await http<{ state: BackendVehicleState }>("/api/v1/vehicle/control", {
    method: "POST",
    headers: authHeaders(),
    body: { ...payload, expected_version: current.state.version },
  });
  return fromBackend(res.state);
}
