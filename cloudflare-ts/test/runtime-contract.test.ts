import { describe, expect, it } from "vitest";
import {
  isRuntimeChatResponseV1,
  isRuntimeErrorResponseV1,
  isRuntimeHealthV1,
  JON2_RUNTIME_CONTRACT_VERSION,
} from "../src/runtime-contract";

describe("Jon2 Python runtime contract v1", () => {
  it("accepts a valid health response while the model is disconnected", () => {
    expect(isRuntimeHealthV1({
      contract_version: JON2_RUNTIME_CONTRACT_VERSION,
      project: "Jon2 AI",
      status: "online",
      api_ready: true,
      model_ready: false,
      model_status: "not_connected",
    })).toBe(true);
  });

  it("rejects health data without the expected contract version", () => {
    expect(isRuntimeHealthV1({
      project: "Jon2 AI",
      status: "online",
      api_ready: true,
      model_ready: true,
      model_status: "ready",
    })).toBe(false);
  });

  it("accepts only a non-empty real reply payload", () => {
    expect(isRuntimeChatResponseV1({
      contract_version: "1",
      project: "Jon2 AI",
      reply: "أهلًا!",
    })).toBe(true);
    expect(isRuntimeChatResponseV1({
      contract_version: "1",
      project: "Jon2 AI",
      reply: "  ",
    })).toBe(false);
  });

  it("recognizes structured runtime errors", () => {
    expect(isRuntimeErrorResponseV1({
      contract_version: "1",
      error: "model_not_ready",
      detail: "No approved checkpoint is loaded.",
    })).toBe(true);
    expect(isRuntimeErrorResponseV1({
      contract_version: "1",
      error: "",
    })).toBe(false);
  });
});
