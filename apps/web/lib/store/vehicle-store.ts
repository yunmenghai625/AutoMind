"use client";

import { create } from "zustand";
import { API_MODE } from "@/lib/config";
import { controlVehicle } from "@/lib/api/vehicleApi";
import {
  DEFAULT_VEHICLE_STATE,
  type VehicleState,
  type VehicleControlAction,
} from "@/types/vehicle";

/**
 * Vehicle state store.
 * Shared by both the AI Agent path and the manual cockpit controls:
 * they both mutate the SAME Vehicle State.
 *
 * Live mode updates only from the authoritative backend response. Local
 * optimistic state is restricted to explicit development Mock mode.
 */
interface VehicleStore {
  vehicle: VehicleState;
  setVehicle: (v: VehicleState) => void;
  apply: (action: VehicleControlAction) => void;
}

export const useVehicleStore = create<VehicleStore>((set) => ({
  vehicle: DEFAULT_VEHICLE_STATE,
  setVehicle: (vehicle) => set({ vehicle }),
  apply: (action) => {
    if (API_MODE === "live") {
      void controlVehicle(action)
        .then((next) => {
          if (next) set(() => ({ vehicle: next }));
        })
        .catch(() => {
          // Keep the last authoritative state when the backend rejects a write.
        });
      return;
    }

    set(({ vehicle }) => {
      const next = { ...vehicle };
      switch (action.kind) {
        case "ac":
          next.acStatus = action.value;
          break;
        case "climate": {
          if (action.zone === "driver") next.driverTemperature = action.value;
          else next.passengerTemperature = action.value;
          break;
        }
        case "seat_heat": {
          if (action.zone === "driver") next.driverSeatHeat = action.value;
          else next.passengerSeatHeat = action.value;
          break;
        }
        case "window": {
          if (action.zone === "FL") next.windowFL = action.value;
          else next.windowFR = action.value;
          break;
        }
        case "headlight":
          next.headlight = action.value;
          break;
        case "speed":
          next.speed = action.value;
          next.gear = action.value > 0 ? "D" : "P";
          break;
        default:
          break;
      }
      return { vehicle: next };
    });

  },
}));
