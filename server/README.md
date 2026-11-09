Jon2 AI API server

Files:
- `server.js`: HTTP API gateway and route wiring.
- `auth.js`: initial account registration, email verification, login, session lookup, CSRF rotation, and logout.
- `db/schema.sql`: PostgreSQL schema foundation.
- `.env.example`: environment variable names and placeholders; never add real secrets here.
- `package.json`: Node 22 runtime and server dependencies.

Important:
- Set secrets only in the backend host's environment settings.
- Apply the SQL schema to a private managed PostgreSQL database before enabling account routes.
- Configure a transactional SMTP provider and a public HTTPS API URL before registration can send verification links.
- GitHub Pages and a separate API host are cross-site. Some mobile browsers block third-party cookies. Use a same-site custom domain for production authentication.
- This is not production-ready until deployed, tested, monitored, and reviewed. No YouTube publishing or AdSense integration is live.


## Public chat release gate

The Node API gateway blocks `POST /api/chat` unless `JON2_CHAT_RELEASE_APPROVED=true` is explicitly set in the server environment. The default is disabled. This is independent of login and CSRF checks: authenticated users are also blocked until the release gate is approved.

Do not set this flag based on CI success, model loading, or automated metrics. Require the exact checkpoint's completed human review record first. The API health response reports `chatReleaseApproved` and `chatEnabled`; `publicLaunchReady` remains false until the broader security and deployment review is complete.

Run the release-gate unit tests with `npm test` or `npm run check`.
