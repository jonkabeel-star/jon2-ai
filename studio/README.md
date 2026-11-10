# Jon2 Studio — Private Bootstrap

This directory contains the first local-only editor prototype for Jon2 AI.

## Current capabilities
- Edit HTML, CSS and JavaScript files in-browser.
- Add simple text/code files.
- Preview the generated HTML in a sandboxed iframe.
- Save the project in this browser's localStorage.
- Export a single file or the project JSON.

## Explicit limitations
- This is not a cloud IDE yet.
- Projects are not uploaded to a server or synchronized across devices.
- It does not execute Python or arbitrary server-side code.
- It does not create a VPS, container, database, or persistent backend.
- Preview is browser-side only and is sandboxed with scripts enabled but without same-origin privileges.
- No login system is implemented in this prototype.
- No public deployment or automatic publishing is enabled.

## Privacy and deployment gate
The repository currently publishes the repository root through GitHub Pages. Do not merge or publish this directory to the production branch until the deployed route is protected by a verified access-control layer that permits only the owner's account.

Preferred deployment gate:
1. Keep the production website unchanged.
2. Put the Studio behind Cloudflare Access (or another verified identity-aware proxy) with a single-user allow policy.
3. Verify that anonymous visitors receive an authentication challenge and cannot fetch Studio assets or APIs directly.
4. Confirm that the Cloudflare account is on a no-charge configuration. Do not enable Workers Paid, paid add-ons, overage billing, or a payment method for this project.
5. Only after the access policy and no-billing configuration are verified, decide whether to publish.

## Free-tier and billing policy
Do not add paid services, paid APIs, paid runners, or automatic plan upgrades. A free-tier quota exhaustion must fail closed rather than switch to a paid plan. Free tiers have provider-defined limits and may change.

## Local data warning
Projects are stored in this browser profile only. Clearing browser site data may erase them. Export the project JSON regularly if it matters.
