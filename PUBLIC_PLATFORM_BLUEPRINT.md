# Jon2 AI — Public Platform Implementation Blueprint

**Status:** design and security baseline; this document does not claim that accounts, video rendering, YouTube publishing, or advertising are live.

## Product experience

Jon2 AI is intended to be a public Arabic-first AI website. Visitors will be able to register, sign in, use available tools under transparent free-use limits, manage projects, and prepare original videos for their own YouTube channels.

The public website must never describe an unfinished tool as operational. Every tool must show one of: Available, Beta, or Coming soon, based on a real backend capability check.

## Architecture

- **Frontend:** static website hosted on GitHub Pages. It contains no passwords, private tokens, database credentials, or privileged YouTube credentials.
- **API:** Node.js gateway in `server/`, behind HTTPS and an explicit CORS allowlist. It forwards requests only to a server-configured model endpoint.
- **Model runtime:** isolated Python service in `ai_engine/`. Model weights and private training corpora stay outside the public Git repository.
- **Database:** managed PostgreSQL for users, sessions, projects, usage records, consent records, and video-job state. Do not use process memory or a public GitHub file as the production database.
- **Object storage:** private storage for user uploads, generated media, and export files. Use short-lived signed links; do not expose private bucket contents.
- **Background jobs:** a queue and worker for image/video/audio generation and YouTube uploads. Long-running jobs must not run inside a normal web request.
- **Secrets:** host-managed environment secrets only. Rotate credentials after accidental exposure.

## Account security — required before public accounts

1. Registration and login must be implemented on the server, not simulated in browser JavaScript.
2. Store passwords only as Argon2id hashes with unique salts. Never store or log plaintext passwords.
3. Use verified email before enabling sensitive account actions.
4. Use secure, HttpOnly, SameSite cookies for sessions; rotate session identifiers after login and privilege changes.
5. Add CSRF protection for cookie-authenticated state changes, login throttling, password-reset expiry, and account recovery protections.
6. Enforce per-user authorization on every project, file, generation, and usage query. A user must never access another user's records by changing an ID.
7. Add audit events for sign-in, password changes, OAuth connection/revocation, and publishing actions. Do not log passwords, access tokens, or private prompt contents.
8. Provide account deletion and a documented data-retention policy.
9. Require HTTPS. Keep CORS restricted to the production site and approved development origins.
10. Add shared, persistent rate limits before public launch. The current in-process limiter is only a temporary safety guard and resets on restart; it is not a production abuse-control system.

## AI tools and model honesty

- The Jon2 model foundation currently starts with random weights. It is not a capable trained assistant yet.
- Do not expose the random-weight prototype as a useful general chat model.
- Mark a tool Available only after its model/runtime, storage, error handling, limits, and quality checks work end to end.
- Keep each user's prompts and generated files private by default.
- Apply fair-use quotas server-side. Show remaining usage and reset periods honestly; do not silently create paid usage.

## Video Studio and YouTube workflow

1. User enters an original idea and selects a format, language, duration, and audience.
2. The system generates a script and scene plan using original material or material with documented permissions.
3. A rights/safety checklist runs before generation: user confirms ownership or permission for uploaded assets, music, voice, logos, and any third-party elements.
4. Generate scenes, voice, captions, and edit instructions using only assets the user owns, commissioned assets, or assets with verified permissions for the intended use.
5. Save a private draft and preview. Show the exact title, description, thumbnail, and video before upload.
6. Require the channel owner to review and explicitly approve each upload. The default is **approval required**; no unattended publishing.
7. Connect a YouTube channel using Google's official OAuth consent flow. Request the minimum scopes needed, explain them, and allow disconnect/revocation.
8. Encrypt refresh tokens at rest using a managed key service. Never send tokens to the browser, commit them to GitHub, or put them in logs.
9. Upload through the official YouTube Data API, record the returned video ID, and show upload status and any API errors.
10. Add scheduling only after the approval workflow is reliable. Approval must be tied to the exact video version being uploaded; edits after approval invalidate it.

### Publishing safeguards

- No automatic public upload without an explicit approval event tied to the exact draft/version.
- Default visibility should be private or unlisted for the first test upload, chosen by the channel owner.
- Never bypass YouTube API quota, OAuth, spam, or platform policies.
- Provide duplicate-upload prevention using a stable job ID and idempotency key.
- Stop the job if rights evidence is missing, the destination channel is unclear, or the user revokes access.

## Advertising and Google AdSense readiness

- AdSense is a later integration, not currently connected or approved.
- Build clean page layouts with clearly reserved ad slots, but do not render fake ads or imitate Google ad UI.
- Ads must be clearly distinguishable from tool controls and generated content.
- Do not require ad clicks, reward clicks, ask users to click, or force an ad interaction to unlock a tool.
- Do not promise one ad for every tool action. Ad display and monetization depend on Google's eligibility, policy review, traffic, and ad-serving decisions.
- Do not send prompts, uploaded files, generated content, passwords, or other sensitive data to advertising scripts.
- Publish accurate privacy, cookie, terms, contact, and content-ownership pages before applying.
- Add the official ad code only after account/site approval and policy review.

## Copyright and content provenance

- Prefer project-authored scripts, user-authored prompts, and assets created by Jon2 or commissioned with written rights.
- Do not scrape books, websites, social networks, videos, or music for training or generation.
- Do not approve a dataset because its packaging has an open license if the underlying text/media rights are unclear.
- Record creator, source, license/permission, allowed uses, attribution requirements, and review date for every third-party asset.
- If the permission is ambiguous, quarantine the asset and ask the owner before use.
- Offer users a way to report infringing content and a process to remove or disable disputed material.

## Launch gates

Do not call Jon2 AI a public production AI service until all are complete:
- Real backend deployment on a suitable host with HTTPS, persistent database, backups, and monitoring.
- Secure registration/login, email verification, account recovery, and deletion tested.
- Per-user isolation, rate limits, abuse reporting, and security review passed.
- Model quality and safety evaluation completed on permitted data.
- Video generation tested with original/licensed assets.
- YouTube OAuth, approval gate, private test upload, revocation, and duplicate prevention tested.
- Privacy policy, terms, content policy, and support contact published.
- AdSense eligibility and approval obtained before ads are enabled.

## Current implementation note

The Node API gateway has been hardened with an explicit CORS allowlist, bounded request body, message length cap, and a temporary per-process rate limit. It still has **no account system, persistent database, production-grade shared rate limiting, or YouTube integration**. GitHub Pages remains a static frontend and cannot host the Python model or secure account database.
