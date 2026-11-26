# Vercel frontend deployment

This repository contains both the browser application and Python/server-side project code.
The Vercel configuration intentionally allowlists only the browser-facing files:

- `index.html`
- root-level JavaScript files
- `manifest.webmanifest`
- SVG files in `assets/`
- browser runtime JavaScript files in `pocket/`

The Python engine, server source, training data, checkpoints, notebooks, and other repository
files are not part of the Vercel static deployment output.

## Important boundaries

- This is a static frontend deployment only. It does not host or run the original Jon2 model.
- Do not set `window.JON2_API_BASE_URL` to an unverified endpoint.
- Keep the chat release gate in place until the original model passes the project's quality
  evaluation and the owner completes human review.
- The GitHub Pages site remains unchanged by this configuration.
- A production deployment requires a separate explicit approval and a successful preview review.
