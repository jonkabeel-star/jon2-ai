# Jon2 Studio — Local-first Prototype

This directory contains the local-first Jon2 Studio editor and Jon2 Bot.

## Current capabilities
- Edit HTML, CSS and JavaScript files in-browser.
- Add simple text/code files.
- Preview the generated HTML in a sandboxed iframe.
- Save the project in this browser's localStorage.
- Export a single file or the project JSON.
- Jon2 Bot can run the built-in static project checks, apply only supported safe fixes, undo its last change, and generate a starter landing page or simple HTML/CSS/JS files.

## No external server required
The current Studio and Bot frontend do not require Oracle Cloud, a Linux VPS, a Python API, or an external AI provider. The Bot runs deterministic local commands in the browser and does not upload project files. It is not yet a general-purpose language model and cannot autonomously reason about arbitrary requests or build complex applications. Do not describe it as a fully trained AI model.

## Explicit limitations
- This is not a cloud IDE yet.
- Projects are stored in this browser profile only; they are not synchronized across devices.
- Clearing browser site data may erase projects. Export the project JSON regularly.
- It does not execute Python or arbitrary server-side code.
- It does not create a VPS, container, database, or persistent backend.
- Preview is browser-side only and sandboxed with scripts enabled but without same-origin privileges.
- No login system or multi-user collaboration is implemented.
- No public deployment or automatic publishing of user projects is enabled.

## Deployment and privacy gate
Keep the Studio branch separate from the production branch until access control and the deployment target have been reviewed. Do not merge PR #40 into the production branch without explicit approval. Verify Cloudflare Pages branch settings and access policy before treating the Studio as private. A public Pages URL is not private merely because its source branch has a private-sounding name.

## Free-tier policy
Do not add paid services, paid APIs, paid runners, or automatic plan upgrades. Free-tier quotas and provider policies can change; never promise lifetime availability.
