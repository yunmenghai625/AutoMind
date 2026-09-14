import type { GarageVehicle, RecallRecord } from "@/types/vehicle";

export const MOCK_GARAGE_VEHICLE: GarageVehicle = {
  name: "2024 AutoMind 演示电动车",
  vin: "AMX8492K1D5E76013",
  mileageKm: 12842,
  batterySoc: 78,
  lastCheck: "今天",
  batteryHealth: 96,
  trim: "长续航版",
  color: "午夜灰",
};

export const MOCK_RECALLS: RecallRecord[] = [
  {
    id: "REC-2025-0047",
    component: "电池管理系统固件",
    risk: "Medium",
    issuedAt: "2025-08-14",
    recommendedAction:
      "请前往最近的服务中心免费将 BMS 固件升级至 v4.2.1。",
  },
];
