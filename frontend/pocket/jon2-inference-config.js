// These values mirror ai_engine/chat_engine.py and ai_engine/jon2_core.py.
export const JON2_SAFARI_MAX_NEW_TOKENS = 256;
export const JON2_SAFARI_GENERATION_OPTIONS = Object.freeze({
  temperature: 1.0,
  repetitionPenalty: 1.10,
  noRepeatNgramSize: 3,
  topK: 0,
  doSample: false
});
