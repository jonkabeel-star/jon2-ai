"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  isChatReleaseApproved,
  getChatReleaseBlock,
} = require("./release-gate");

test("chat release is blocked by default when the flag is absent", () => {
  assert.equal(isChatReleaseApproved({}), false);
  const result = getChatReleaseBlock({});
  assert.equal(result.status, 503);
  assert.equal(result.body.code, "JON2_CHAT_RELEASE_BLOCKED");
});

test("false, empty, and non-exact values never enable chat", () => {
  for (const value of ["false", "", "TRUE", " true ", "1"]) {
    assert.equal(isChatReleaseApproved({ JON2_CHAT_RELEASE_APPROVED: value }), false);
    assert.equal(getChatReleaseBlock({ JON2_CHAT_RELEASE_APPROVED: value }).status, 503);
  }
});

test("only the exact explicit true value opens the release gate", () => {
  const env = { JON2_CHAT_RELEASE_APPROVED: "true" };
  assert.equal(isChatReleaseApproved(env), true);
  assert.equal(getChatReleaseBlock(env), null);
});
