import type { GarageVehicle, RecallRecord } from "@/types/vehicle";

export const MOCK_GARAGE_VEHICLE: GarageVehicle = {
  name: "2024 AutoMind Demo EV",
  vin: "AMX8492K1D5E76013",
  mileageKm: 12842,
  batterySoc: 78,
  lastCheck: "Today",
  batteryHealth: 96,
  trim: "Long Range",
  color: "Midnight Grey",
};

export const MOCK_RECALLS: RecallRecord[] = [
  {
    id: "REC-2025-0047",
    component: "Battery Management System Firmware",
    risk: "Medium",
    issuedAt: "2025-08-14",
    recommendedAction:
      "Update BMS firmware to v4.2.1 at your nearest service center. No cost.",
  },
];
