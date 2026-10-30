# Jon2 AI — Authentication Setup and Deployment Checklist

## What is implemented in code

- `POST /api/auth/register`: validates email and password, hashes the password with Argon2id, creates a pending account, and emails a one-time verification link.
- `POST /api/auth/resend-verification`: sends a replacement link for an unverified account without revealing whether an account exists.
- `GET /api/auth/verify`: displays a confirmation page. It does not consume the token merely because an email security scanner opened the link.
- `POST /api/auth/verify`: consumes the one-time token and activates the account.
- `POST /api/auth/login`: checks the password and verified status, then creates a server-side session.
- `GET /api/auth/me`: validates the session and returns a fresh CSRF token.
- `POST /api/auth/logout`: validates CSRF and revokes the server-side session.

Passwords use Argon2id. Raw session and verification tokens are not stored in PostgreSQL; only SHA-256 token hashes are stored. The browser session cookie is Secure, HttpOnly, and SameSite=None for the current cross-origin hosting arrangement.

## Required before enabling registration

1. Create a private managed PostgreSQL database with backups and TLS.
2. Configure the backend host to use Node.js 22 or newer.
3. Set the environment variables from `.env.example` in the backend host's private settings. Do not put real values in GitHub.
4. Run `npm install` in the `server` directory.
5. Run `npm run migrate` in the `server` directory once to apply `db/schema.sql`.
6. Configure a transactional SMTP provider and verify that its sender domain is authorized.
7. Set `JON2_API_PUBLIC_URL` to the actual HTTPS API origin and `JON2_ALLOWED_ORIGINS` to the exact frontend origin.
8. Deploy the API and test health, registration, email delivery, verification, login, session refresh, logout, expired tokens, and rate limits.
9. Establish a same-site custom domain for the frontend and API before public launch. GitHub Pages and a separate API hostname are cross-site; mobile Safari and other browsers may block third-party cookies even when SameSite=None is set.
10. Add persistent distributed rate limiting, password reset, account deletion, audit monitoring, security headers, backups, and an independent security review before public multi-user use.

## Important limitations

- This repository change does not create a database, email account, backend hosting service, or custom domain.
- The account endpoints are not live until deployment and secret configuration are completed.
- The current rate limiter is process-local and is not suitable as the only production abuse defense.
- There is no password-reset endpoint yet.
- The current static frontend has not yet been connected to these account endpoints.
- Do not ask users to enter database passwords, SMTP credentials, OAuth secrets, or other server secrets into the website or chat.

## API request examples

Register:

```http
POST /api/auth/register
Content-Type: application/json

{"email":"person@example.com","password":"use-a-long-unique-passphrase"}
```

Login:

```http
POST /api/auth/login
Content-Type: application/json

{"email":"person@example.com","password":"use-the-same-passphrase"}
```

The login response sets the HttpOnly session cookie and returns a CSRF token. Keep the CSRF token in page memory and send it in the `X-CSRF-Token` header on state-changing authenticated requests. Do not put session tokens or credentials in localStorage.
