// Browser-side surface-integrity checks for Jon2 Arabic output.
// These checks detect common corruption patterns; they cannot prove meaning or factuality.
const ALLOWED_ANSWER = /^[\u0600-\u06FF\s،؛؟.!…ـ0-9٠-٩()«»"'\-]+$/u;
const ARABIC_LETTERS = /[\u0621-\u064A\u066E-\u06D3]/gu;
const ARABIC_WORDS = /[\u0621-\u064A\u066E-\u06D3]+/gu;

export function diagnoseJon2ArabicAnswer(answer) {
  const text = typeof answer === "string" ? answer.trim() : "";
  const visible = Array.from(text).filter(char => !/\s/u.test(char));
  const words = text.match(ARABIC_WORDS) || [];
  const arabicCount = (text.match(ARABIC_LETTERS) || []).length;
  const shortWords = words.filter(word => Array.from(word).length <= 2).length;
  const uniqueWords = new Set(words);
  const warnings = [];

  if (!text) warnings.push("empty_answer");
  if (Array.from(text).length < 4) warnings.push("too_short");
  if (Array.from(text).length > 4000) warnings.push("too_long");
  if (text && !ALLOWED_ANSWER.test(text)) warnings.push("unsupported_characters");
  if (arabicCount / Math.max(1, visible.length) < 0.70) warnings.push("low_arabic_character_ratio");
  if (/(.)\1{3,}/u.test(text) || /(.{2,8})\1{2,}/u.test(text)) warnings.push("character_or_phrase_loop");

  // Fragmented output often consists of many isolated one- or two-letter
  // Arabic pieces. Preserve concise answers; apply this check only to longer
  // responses, and use it as a corruption signal rather than a semantic score.
  const shortWordRatio = shortWords / Math.max(1, words.length);
  const averageWordLength = words.reduce((sum, word) => sum + Array.from(word).length, 0) / Math.max(1, words.length);
  const articlePrefixRatio = words.filter(word => word.startsWith("ال") || word.startsWith("وال")).length / Math.max(1, words.length);
  if (words.length >= 8 && (
    (shortWordRatio > 0.60 && averageWordLength < 3.2) ||
    (articlePrefixRatio > 0.70 && averageWordLength < 5.2)
  )) {
    warnings.push("fragmented_arabic_word_sequence");
  }

  const uniqueWordRatio = uniqueWords.size / Math.max(1, words.length);
  if (words.length >= 8 && uniqueWordRatio < 0.45) warnings.push("low_unique_word_ratio");
  if (words.length >= 8) {
    for (const size of [1, 2, 3]) {
      for (let i = 0; i <= words.length - 3 * size; i++) {
        const a = words.slice(i, i + size).join("\u0000");
        const b = words.slice(i + size, i + 2 * size).join("\u0000");
        const c = words.slice(i + 2 * size, i + 3 * size).join("\u0000");
        if (a === b && b === c) warnings.push("repeated_ngram");
      }
    }
  }

  return {
    characterCount: Array.from(text).length,
    wordCount: words.length,
    arabicCharacterRatio: Number((arabicCount / Math.max(1, visible.length)).toFixed(3)),
    shortWordRatio: Number(shortWordRatio.toFixed(3)),
    averageWordLength: Number(averageWordLength.toFixed(3)),
    uniqueWordRatio: Number(uniqueWordRatio.toFixed(3)),
    warnings: [...new Set(warnings)],
    semanticReviewRequired: true
  };
}

export function validateJon2ArabicAnswer(answer) {
  if (typeof answer !== "string") return false;
  const text = answer.trim();
  const report = diagnoseJon2ArabicAnswer(text);
  if (report.characterCount < 4 || report.characterCount > 4000) return false;
  if (!ALLOWED_ANSWER.test(text)) return false;
  return report.warnings.length === 0;
}
