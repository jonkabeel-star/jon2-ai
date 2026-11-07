/**
 * Jon2 AI v1 runtime contract.
 *
 * This file defines the wire format only. It does not connect to or select
 * a model runtime, and must not contain credentials or model weights.
 */

export const JON2_API_VERSION = "1" as const;

export type ChatRole = "user" | "assistant";

export interface ChatMessage {
  role: ChatRole;
  content: string;
}

export interface ChatRequestV1 {
  api_version: typeof JON2_API_VERSION;
  message: string;
  history?: ChatMessage[];
  request_id?: string;
}

export interface RuntimeHealthV1 {
  project: "Jon2 Cloud";
  api_version: typeof JON2_API_VERSION;
  api_ready: boolean;
  model_ready: boolean;
  model_status: "ready" | "loading" | "not_connected" | "error";
}

export interface ChatSuccessV1 {
  project: "Jon2 Cloud";
  api_version: typeof JON2_API_VERSION;
  request_id?: string;
  model: string;
  reply: string;
}

export interface ChatErrorV1 {
  project: "Jon2 Cloud";
  api_version: typeof JON2_API_VERSION;
  error: string;
  message: string;
  request_id?: string;
}

const MAX_MESSAGE_LENGTH = 2_000;
const MAX_HISTORY_ITEMS = 8;
const MAX_HISTORY_CONTENT_LENGTH = 2_000;

export function isChatRole(value: unknown): value is ChatRole {
  return value === "system" || value === "user" || value === "assistant";
}

/** Validate untrusted JSON before it is forwarded to a model runtime. */
export function isChatRequestV1(value: unknown): value is ChatRequestV1 {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;

  const candidate = value as Record<string, unknown>;
  if (candidate.api_version !== JON2_API_VERSION) return false;
  if (typeof candidate.message !== "string") return false;

  const message = candidate.message.trim();
  if (!message || message.length > MAX_MESSAGE_LENGTH) return false;

  if (candidate.request_id !== undefined &&
      (typeof candidate.request_id !== "string" ||
       candidate.request_id.length > 128)) return false;

  if (candidate.history === undefined) return true;
  if (!Array.isArray(candidate.history) ||
      candidate.history.length > MAX_HISTORY_ITEMS) return false;

  return candidate.history.every((item: unknown) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return false;
    const entry = item as Record<string, unknown>;
    return isChatRole(entry.role) &&
      typeof entry.content === "string" &&
      entry.content.length <= MAX_HISTORY_CONTENT_LENGTH;
  });
}

/** Normalize transport failures without leaking upstream details or secrets. */
export function normalizeRuntimeError(
  status: number,
): Pick<ChatErrorV1, "error" | "message"> {
  if (status === 408 || status === 504) {
    return {
      error: "runtime_timeout",
      message: "انتهت مهلة انتظار محرك Jon2.",
    };
  }
  if (status === 401 || status === 403) {
    return {
      error: "runtime_unauthorized",
      message: "تعذّر التحقق من صلاحية الاتصال بمحرك Jon2.",
    };
  }
  return {
    error: "runtime_unavailable",
    message: "محرك Jon2 غير متاح حاليًا.",
  };
}
