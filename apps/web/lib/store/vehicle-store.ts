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
 * Live mode write-through: after the local optimistic update, the action is
 * posted to the FastAPI backend (POST /api/v1/vehicle/control) and the
 * authoritative response state replaces the local value. Backend-rejected
 * actions keep the local optimistic value (Phase 1 backend cannot persist
 * AC / speed, which controlVehicle skips anyway).
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

    if (API_MODE === "live") {
      void controlVehicle(action)
        .then((next) => {
          if (next) set(() => ({ vehicle: next }));
        })
        .catch(() => {
          // Keep the local optimistic value when the backend rejects the write.
        });
    }
  },
}));
