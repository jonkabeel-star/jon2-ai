// Explicit fail-closed policy for the private Safari checkpoint.
// Loading and fingerprint verification do not establish language quality.
export function canUseJon2SafariChat({releaseApproved=false,modelLoaded=false,qualityReviewPassed=false}={}) {
  return releaseApproved === true && modelLoaded === true && qualityReviewPassed === true;
}
