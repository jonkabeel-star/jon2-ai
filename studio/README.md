# Jon2 Studio — AI-assisted coding workspace

Jon2 Studio is a browser-based code workspace. The current branch adds a protected AI coding endpoint for Jon2 Bot.

## What the AI agent can do
- Read the current project files sent from the editor.
- Understand natural-language requests in Arabic or English.
- Propose complete new or updated HTML, CSS, JavaScript, JSON, Markdown, and text files.
- Apply validated file changes to the browser workspace, refresh the preview, and keep local undo history.
- Run the built-in static checks and apply a small set of safe local repairs.

The model proposes file contents; the browser validates paths and applies the changes locally. It cannot access the user's GitHub repository, Cloudflare dashboard, device filesystem, terminal, Linux, Python/Node runtime, databases, or publish projects. It does not execute generated server-side code.

## AI provider and free-tier behavior
The API route uses Cloudflare Workers AI model `@cf/zai-org/glm-4.7-flash`. Cloudflare currently lists this model as available on Workers Free. Workers AI includes 10,000 Neurons per day at no charge on Workers Free. If the free allocation or a model limit is exceeded, requests fail; do not upgrade or enable paid billing to bypass it. Free limits and model availability can change. This is not a lifetime-free guarantee.

Official references:
- https://developers.cloudflare.com/workers-ai/models/glm-4.7-flash/
- https://developers.cloudflare.com/workers-ai/platform/pricing/

## Required Cloudflare configuration
The agent intentionally remains unavailable until both Workers AI and Cloudflare Access are configured. This prevents an unprotected public endpoint from consuming the account's AI quota.

1. In the Cloudflare Pages project `jon2-studio`, open **Settings → Functions → Bindings**.
2. Add a **Workers AI** binding with variable name `AI`. Do not select a paid plan or add billing.
3. Protect the production hostname and preview hostnames with Cloudflare Access. Use an **Allow** policy for your own login identity only; do not allow Everyone.
4. In the Pages project's production and preview environment variables, add:
   - `ACCESS_TEAM_DOMAIN`: your Cloudflare Access team domain, for example `your-team.cloudflareaccess.com` (without `https://`).
   - `ACCESS_AUD`: the Audience (AUD) tag shown in the Access application's settings.
5. Save and redeploy the Pages project.

The Function verifies the Cloudflare Access JWT signature, issuer, audience, and expiry before calling Workers AI. Do not put tokens, passwords, or private keys in the repository or chat.

## Project storage and privacy
- Project files are stored in this browser's localStorage. Export a project backup regularly.
- To generate or edit files, the current prompt and project file contents are sent to Cloudflare Workers AI through the protected Pages Function. Do not send passwords, API keys, or confidential data.
- The model response is validated for safe relative file paths and size limits before the browser applies it.
- The agent does not delete files, access external websites, execute terminal commands, or publish projects.
- The preview runs in a sandboxed iframe with scripts enabled but without same-origin privileges.

## Deployment safety
- The Studio branch is `jon2-studio-private-bootstrap`.
- Do not merge PR #40 into `main` without explicit approval.
- The original Jon2 AI site is separate and must not be changed by this Studio work.
- A `noindex` tag or private-sounding branch name does not make a public URL private. Verify Cloudflare Access in a private browser window before sharing the Studio URL.
