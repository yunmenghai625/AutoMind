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
        "操作已拒绝——安全防护已拦截车门解锁操作。",
        "车辆速度大于 0 km/h。只有车辆静止且挡位处于 P 挡时才允许解锁车门。",
      ),
      assistant(
        "现在不能执行开门操作——车辆正以 120 km/h 行驶。安全策略要求车速为 0 km/h 且挡位处于 P 挡。请先安全停车，我再为你解锁车门。",
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
        toolStatus("set_temperature", { zone: "前排乘客", target: 25 }, "SUCCESS", 9),
      ),
      assistant(
        "好的，已将前排乘客（妈妈一侧）的温度设置为 25°C。",
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
        toolStatus("set_temperature", { zone: "主驾", target: 24 }, "SUCCESS", 9),
      ),
      toolMessage(
        toolStatus("set_seat_heating", { zone: "主驾", level: 1 }, "SUCCESS", 7),
      ),
      assistant(
        "已将主驾温度调至 24°C，并开启 1 挡座椅加热。正在升温，如果还觉得冷可以继续告诉我。",
        { latencyMs: 420 },
      ),
    ];
    return { send: { messages }, nextVehicle: vehicleNow };
  }

  // ---- Generic intents -----------------------------------------------------
  const responses: Array<{ pattern: RegExp; text: string }> = [
    {
      pattern: /battery|电量|续航|range/i,
      text: `当前电量为 ${vehicle.batterySoc}%，预计续航 ${vehicle.rangeKm} km。按照你的日常出行习惯，这些电量足以覆盖常规通勤，并留有充足余量。`,
    },
    {
      pattern: /hello|hi|你好|hey/i,
      text: "你好！我是 AutoMind 智能座舱助手。可以对我说“我有点冷”，也可以询问车辆电量或车门控制。",
    },
    {
      pattern: /help|帮助|能做什么|what can you do/i,
      text: "我可以控制空调和座椅、根据车辆手册回答问题、协助诊断仪表警告，并在操作存在风险时进行安全提醒。",
    },
  ];

  const hit = responses.find((r) => r.pattern.test(t));
  return {
    send: {
      messages: [
        assistant(
          hit
            ? hit.text
            : "我理解你的需求，但当前 AutoMind 演示模式只支持部分指令。可以试试：“我有点冷”“我妈有点冷”“120 公里时速帮我打开车门”或“我的电量还够吗”。",
          { latencyMs: 420 },
        ),
      ],
    },
    nextVehicle: vehicleNow,
  };
}
