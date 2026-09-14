import type {
  ChatMessage,
  SendChatResponse,
  ToolCall,
} from "@/types/chat";
import type { VehicleState } from "@/types/vehicle";

let seq = 0;
export function uid(prefix = "msg"): string {
  seq += 1;
  return `${prefix}_${Date.now().toString(36)}_${seq}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

const toolStatus = (name: string, params: ToolCall["params"], status: ToolCall["status"], durationMs?: number): ToolCall => ({
  name,
  params,
  status,
  durationMs,
});

function toolMessage(tool: ToolCall): ChatMessage {
  return {
    id: uid("tool"),
    role: "assistant",
    kind: "tool_call",
    content: "",
    at: nowIso(),
    tools: [tool],
  };
}

function assistant(content: string, meta?: ChatMessage["meta"]): ChatMessage {
  return {
    id: uid(),
    role: "assistant",
    kind: "assistant",
    content,
    at: nowIso(),
    meta,
  };
}

function safety(content: string, reason: string): ChatMessage {
  return {
    id: uid("safety"),
    role: "assistant",
    kind: "safety_warning",
    content,
    at: nowIso(),
    meta: { blocked: true, safetyReason: reason },
  };
}

export interface MockChatOutcome {
  send: SendChatResponse;
  nextVehicle: VehicleState;
}

/**
 * Mock intent engine for the AutoMind Assistant.
 *
 * Deterministic rules reproduce the three required interview demos:
 *   1. "I'm a bit cold"            -> driver 24°C + seat heat 1
 *   2. "My mom is cold"            -> passenger 25°C
 *   3. "Open the door at 120 km/h" -> speed 120, Safety Policy BLOCKED
 * Anything else falls through to a generic assistant reply (no vehicle change).
 */
export function mockChatReply(
  input: string,
  vehicle: VehicleState,
): MockChatOutcome {
  const t = input.toLowerCase();
  const vehicleNow: VehicleState = { ...vehicle };

  // ---- Demo 3: door unlock while moving (safety block) --------------------
  const wantsDoor =
    /打开车门|开门|unlock|open.{0,6}door/i.test(t) ||
    (t.includes("door") && (t.includes("open") || t.includes("unlock")));
  const mentionsSpeed =
    /120|时速.*(12[0-9]|1[0-2][0-9])|speed/i.test(t);

  if (wantsDoor) {
    // Reproduce the blocked scenario: first raise speed to 120
    if (/120|时速|speed/i.test(t)) {
      vehicleNow.speed = 120;
      vehicleNow.gear = "D";
    }
    const messages: ChatMessage[] = [
      toolMessage(
        toolStatus(
          "door_unlock",
          { zone: "driver_door", speed: vehicleNow.speed },
          "BLOCKED",
          9,
        ),
      ),
      safety(
        "Operation Rejected — door_unlock blocked by Safety Guard.",
        "Vehicle speed > 0 km/h. Door unlock is only allowed when the vehicle is stationary and in Park.",
      ),
      assistant(
        "I can't do that — we're moving at 120 km/h. Safety policy prevents door unlock while the vehicle is in motion (speed must be 0 km/h and gear in P). Please stop the car first and I'll unlock it for you.",
        { blocked: true, latencyMs: 312 },
      ),
    ];
    return { send: { messages }, nextVehicle: vehicleNow };
  }

  // ---- Demo 1 / 2: temperature intents ------------------------------------
  const passengerIntent =
    /妈|mother|mom|副驾|passenger/i.test(t);
  const coldIntent = /有点冷|冷|cold|warm|heating|seat.?heat/i.test(t);

  if (passengerIntent && coldIntent) {
    vehicleNow.passengerTemperature = 25;
    const messages: ChatMessage[] = [
      toolMessage(
        toolStatus("set_temperature", { zone: "Front Passenger", target: 25 }, "SUCCESS", 9),
      ),
      assistant(
        "Done — I set the front passenger (Mom) temperature to 25°C.",
        { latencyMs: 420 },
      ),
    ];
    return { send: { messages }, nextVehicle: vehicleNow };
  }

  if (coldIntent) {
    vehicleNow.driverTemperature = 24;
    vehicleNow.driverSeatHeat = 1;
    const messages: ChatMessage[] = [
      toolMessage(
        toolStatus("set_temperature", { zone: "Driver", target: 24 }, "SUCCESS", 9),
      ),
      toolMessage(
        toolStatus("set_seat_heating", { zone: "Driver", level: 1 }, "SUCCESS", 7),
      ),
      assistant(
        "I've raised the driver temperature to 24°C and switched on seat heating (level 1). Warming up now — let me know if you'd like it warmer.",
        { latencyMs: 420 },
      ),
    ];
    return { send: { messages }, nextVehicle: vehicleNow };
  }

  // ---- Generic intents -----------------------------------------------------
  const responses: Array<{ pattern: RegExp; text: string }> = [
    {
      pattern: /battery|电量|续航|range/i,
      text: `Your battery is at ${vehicle.batterySoc}% with an estimated range of ${vehicle.rangeKm} km. Based on your drive pattern, that covers your typical commute with plenty of margin.`,
    },
    {
      pattern: /hello|hi|你好|hey/i,
      text: "Hello! I'm AutoMind, your cockpit AI. Try saying \"I'm a bit cold\" or ask me about your battery, or how to open the door.",
    },
    {
      pattern: /help|帮助|能做什么|what can you do/i,
      text: "I can control your climate and seats, answer questions from the vehicle manual, help diagnose dashboard warnings, and remind you about safety policies.",
    },
  ];

  const hit = responses.find((r) => r.pattern.test(t));
  return {
    send: {
      messages: [
        assistant(
          hit
            ? hit.text
            : `I understand what you're asking, but this is running on the AutoMind demo kernel with a limited mock intent set. Try: "I'm a bit cold", "My mom is cold", "Open the door at 120 km/h", or "How's my battery?".`,
          { latencyMs: 420 },
        ),
      ],
    },
    nextVehicle: vehicleNow,
  };
}
