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
