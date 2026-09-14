/**
 * Vehicle / Digital Twin domain types.
 * Mirror of the future FastAPI contract (GET /api/v1/vehicle/state).
 */

export type Gear = "P" | "D" | "R" | "N" | "B";
export type AcStatus = "OFF" | "ON";
export type HeadlightMode = "OFF" | "AUTO" | "ON";
export type ChargeStatus = "IDLE" | "CHARGING" | "COMPLETE";
export type SeatHeatLevel = 0 | 1 | 2 | 3;
export type WindowLevel = 0 | 25 | 50 | 75 | 100;

export interface VehicleState {
  speed: number; // km/h
  gear: Gear;
  batterySoc: number; // 0-100
  rangeKm: number;
  driverTemperature: number; // °C
  passengerTemperature: number; // °C
  driverSeatHeat: SeatHeatLevel;
  passengerSeatHeat: SeatHeatLevel;
  acStatus: AcStatus;
  windowFL: WindowLevel;
  windowFR: WindowLevel;
  headlight: HeadlightMode;
  chargeStatus: ChargeStatus;
}

export type VehicleControlAction =
  | { kind: "ac"; value: AcStatus }
  | { kind: "climate"; zone: "driver" | "passenger"; value: number }
  | { kind: "seat_heat"; zone: "driver" | "passenger"; value: SeatHeatLevel }
  | { kind: "window"; zone: "FL" | "FR"; value: WindowLevel }
  | { kind: "headlight"; value: HeadlightMode }
  | { kind: "speed"; value: number };

export interface ControlResult {
  success: boolean;
  vehicle: VehicleState;
  message?: string;
  blocked?: boolean;
  reason?: string;
}

export const DEFAULT_VEHICLE_STATE: VehicleState = {
  speed: 0,
  gear: "P",
  batterySoc: 78,
  rangeKm: 421,
  driverTemperature: 22,
  passengerTemperature: 22,
  driverSeatHeat: 0,
  passengerSeatHeat: 0,
  acStatus: "OFF",
  windowFL: 0,
  windowFR: 0,
  headlight: "AUTO",
  chargeStatus: "IDLE",
};

export interface GarageVehicle {
  name: string;
  vin: string;
  mileageKm: number;
  batterySoc: number;
  lastCheck: string;
  batteryHealth: number | null;
  trim: string;
  color: string;
}

export interface RecallRecord {
  id: string;
  component: string;
  risk: "Low" | "Medium" | "High";
  issuedAt: string;
  recommendedAction: string;
}

export interface UserDrivePreferences {
  preferredTemperature: number; // °C
  seatHeatingLevel: SeatHeatLevel;
  preferredChargingLimit: number; // %
  preferredDrivingMode: "Comfort" | "Sport" | "Eco";
}
