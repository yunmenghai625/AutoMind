/** AI Chat domain types. Mirror of the future POST /api/v1/chat contract. */

export type ChatRole = "user" | "assistant";

export type MessageKind =
  | "user"
  | "assistant"
  | "tool_call"
  | "tool_result"
  | "safety_warning"
  | "system_event";

export interface ToolCall {
  name: string;
  params: Record<string, string | number | boolean>;
  status: "SUCCESS" | "RUNNING" | "FAILED" | "BLOCKED";
  durationMs?: number;
}

export interface ChatMessage {
  id: string;
  role: ChatRole;
  kind: MessageKind;
  content: string;
  at: string;
  tools?: ToolCall[];
  meta?: {
    model?: string;
    latencyMs?: number;
    blocked?: boolean;
    safetyReason?: string;
    runId?: string;
  };
}

export interface SendChatRequest {
  message: string;
  sessionId?: string;
  history?: Array<{ role: ChatRole; content: string }>;
}

export interface SendChatResponse {
  messages: ChatMessage[]; // appended messages (may be several: tool call + assistant + safety...)
  vehicle?: import("@/types/vehicle").VehicleState;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
}
