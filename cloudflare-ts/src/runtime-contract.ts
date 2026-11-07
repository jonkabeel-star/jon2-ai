/**
 * Versioned boundary between the TypeScript edge gateway and the Python
 * Jon2 model runtime. These types describe the protocol only; they do not
 * connect to a model or make an unavailable runtime appear ready.
 */

export const JON2_RUNTIME_CONTRACT_VERSION = "1" as const;

export interface RuntimeHealthV1 {
  contract_version: typeof JON2_RUNTIME_CONTRACT_VERSION;
  project: "Jon2 AI";
  status: "online" | "ready";
  api_ready: boolean;
  model_ready: boolean;
  model_status: string;
}

export interface RuntimeHistoryMessageV1 {
  role: "user" | "assistant";
  content: string;
}

export interface RuntimeChatRequestV1 {
  contract_version: typeof JON2_RUNTIME_CONTRACT_VERSION;
  message: string;
  history?: RuntimeHistoryMessageV1[];
  session_id?: string;
}

export interface RuntimeChatResponseV1 {
  contract_version: typeof JON2_RUNTIME_CONTRACT_VERSION;
  project: "Jon2 AI";
  reply: string;
  session_id?: string | null;
}

export interface RuntimeErrorResponseV1 {
  contract_version: typeof JON2_RUNTIME_CONTRACT_VERSION;
  error: string;
  detail?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isRuntimeHealthV1(value: unknown): value is RuntimeHealthV1 {
  return (
    isRecord(value) &&
    value.contract_version === JON2_RUNTIME_CONTRACT_VERSION &&
    value.project === "Jon2 AI" &&
    (value.status === "online" || value.status === "ready") &&
    typeof value.api_ready === "boolean" &&
    typeof value.model_ready === "boolean" &&
    typeof value.model_status === "string"
  );
}

export function isRuntimeChatResponseV1(
  value: unknown,
): value is RuntimeChatResponseV1 {
  return (
    isRecord(value) &&
    value.contract_version === JON2_RUNTIME_CONTRACT_VERSION &&
    value.project === "Jon2 AI" &&
    typeof value.reply === "string" &&
    value.reply.trim().length > 0 &&
    (value.session_id === undefined ||
      value.session_id === null ||
      typeof value.session_id === "string")
  );
}

export function isRuntimeErrorResponseV1(
  value: unknown,
): value is RuntimeErrorResponseV1 {
  return (
    isRecord(value) &&
    value.contract_version === JON2_RUNTIME_CONTRACT_VERSION &&
    typeof value.error === "string" &&
    value.error.length > 0 &&
    (value.detail === undefined || typeof value.detail === "string")
  );
}
