/** User drive preferences (stored in localStorage for now).
 * Will be moved to the backend once it exists.
 */

import type { SeatHeatLevel } from "@/types/vehicle";

export interface PreferencesState {
  preferredTemperature: number;
  seatHeatingLevel: SeatHeatLevel;
  preferredChargingLimit: number;
  preferredDrivingMode: "Comfort" | "Sport" | "Eco";
}

export const DEFAULT_PREFERENCES: PreferencesState = {
  preferredTemperature: 23,
  seatHeatingLevel: 1,
  preferredChargingLimit: 80,
  preferredDrivingMode: "Comfort",
};
