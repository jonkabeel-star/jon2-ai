# Jon2 API Key Management (review branch)

This feature is isolated from chat and the original Jon2 model. It adds key issuance, verification, and revocation to the Cloudflare Worker. It does not enable `/api/chat`, call an external AI provider, or alter model/checkpoint files.

## Routes

- `POST /api/keys/issue` — owner-only. Requires `Authorization: Bearer <JON2_MASTER_KEY>`. Returns a new `jon2_live_...` key exactly once.
- `POST /api/keys/verify` — accepts JSON `{"key":"jon2_live_..."}`; returns validity, key id, scopes, and expiry. It never returns the raw key.
- `POST /api/keys/revoke` — owner-only. Requires the master secret and JSON `{"keyId":"<uuid>"}`.

Default scope is `api:read`; allowed scopes are `api:read` and `api:write`. Expiration defaults to 365 days; accepted range is 1–3650 days. This scope metadata is not yet connected to any protected application operation.

## Required Cloudflare setup (manual; no secret belongs in GitHub)

1. Create a Cloudflare D1 database from the Cloudflare dashboard.
2. Open the Worker settings for the existing `jon2-ai` Worker and add a D1 binding named exactly `JON2_DB`, pointing to that database.
3. Apply `migrations/0001_create_jon2_api_keys.sql` to that D1 database using the Cloudflare D1 console.
4. Generate a high-entropy random master secret (at least 32 characters) in a trusted password manager. Do not send it in ChatGPT, place it in the website, or commit it.
5. In Worker Settings → Variables and Secrets, add `JON2_MASTER_KEY` as a **Secret**, not a plaintext variable. Keep it private. The Worker deliberately has no built-in default.
6. Configure the D1 binding and secret only after reviewing this branch. No deployment is performed by this change.

The D1 database and Worker binding are not created by GitHub commits. Cloudflare plan limits and any applicable usage charges are controlled by Cloudflare; this repository does not guarantee unlimited free usage.

## Security properties

- Keys are generated with Web Crypto randomness (32 bytes).
- Only SHA-256 key hashes are stored in D1; plaintext is returned once on issuance.
- The master secret is read only from the Worker secret binding and is never returned.
- Master authentication rejects absent, short, whitespace-padded, or malformed secrets. Both the configured and supplied values are SHA-256 hashed; the resulting fixed 64-character hexadecimal digests are compared over the full fixed length without early exit on the first differing character. This is a constant-work digest comparison in application code, not a claim of mathematically perfect constant-time behavior across the JavaScript runtime and platform.
- Expiration is accepted only when it is a parseable date whose timestamp is finite and strictly greater than the current time. Invalid dates, `NaN`, past dates, and dates exactly equal to now are rejected.
- Verification accepts only records with status `active`; revoked keys are rejected.
- Stored scope JSON must parse to a non-empty array containing only the currently allowed scopes; corrupt or unsupported scope records fail closed.
- CORS remains restricted to the existing allowlist; preflight permits only Content-Type and Authorization.
- Request bodies are size-limited; unknown scopes and invalid expiration are rejected.
- Error responses do not echo secrets or raw database errors.
- No key value is written to logs, HTML, localStorage, or repository configuration.

## Tests

Run from the repository root with Node.js 22 or later:

```sh
node --test cloudflare/tests/api-keys.test.mjs
```

The regression suite covers missing D1, missing/weak/wrong/correct master secrets, valid subkey verification, revoked keys, expired keys, expiry equal to the current time, malformed expiry dates, unknown keys, disallowed scopes, duplicate scopes, invalid expiration settings, and unchanged chat fail-closed behavior.

The dedicated GitHub Actions workflow `.github/workflows/jon2-api-key-tests.yml` runs this command on relevant pull-request changes. A passing test run must be confirmed in the Actions UI before treating this branch as test-verified.

## Important boundaries

- This is a key-management service, not an AI model and not a chat integration.
- No API key is embedded in `index.html`; the existing local-only UI panel remains unconnected and should not be used to store the owner master secret.
- No key is automatically authorized for chat, memory, rules, data changes, or model runtime.
- The existing `/api/chat` behavior is unchanged and continues to return HTTP 503.
- A production deployment still requires review, Cloudflare D1 provisioning, secret configuration, and security testing. None is performed by this branch.
