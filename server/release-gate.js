"use strict";

const RELEASE_BLOCK_MESSAGE =
  "المحادثة غير مفعلة حتى اكتمال مراجعة النموذج والحصول على موافقة الإصدار.";

function isChatReleaseApproved(env = process.env) {
  return env.JON2_CHAT_RELEASE_APPROVED === "true";
}

function getChatReleaseBlock(env = process.env) {
  if (isChatReleaseApproved(env)) return null;
  return {
    status: 503,
    body: {
      error: RELEASE_BLOCK_MESSAGE,
      code: "JON2_CHAT_RELEASE_BLOCKED",
    },
  };
}

module.exports = {
  isChatReleaseApproved,
  getChatReleaseBlock,
};
