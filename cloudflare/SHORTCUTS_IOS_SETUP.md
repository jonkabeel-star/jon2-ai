# iPhone Shortcuts: issue and verify a Jon2 API key

This guide uses the existing Worker routes. It does not change the Worker, deploy anything, or connect an API key to chat or memory.

## Important distinction

- `JON2_MASTER_KEY` is the owner-only secret. It is used only when issuing or revoking keys.
- `jon2_live_...` is the personal API key. Use this for verification and later API requests.
- Do not use the personal key as the master secret, and do not put either key in GitHub, a website, or a shared screenshot.

## Shortcut A — issue a personal key (only when you need a new key)

Create a separate shortcut named `JON2 - Issue Personal Key`.

1. Add **Ask for Input**. Set the input type to **Text** and prompt: `Enter JON2_MASTER_KEY`. This is the one-time owner authorization for issuance; it is not the personal key.
2. Add **Get Contents of URL** with URL `https://jon2-ai.jonkabeel.workers.dev/api/keys/issue`.
3. Set Method to **POST**.
4. Under **Headers**, add exactly one header:
   - Key: `Authorization`
   - Value: `Bearer ` followed by the Ask for Input result.
5. Set Request Body to **JSON** and add:
   - `label` = `iPhone personal key`
   - `scopes` = a List containing `api:read`
   - `expirationDays` = `365`
6. Run it. A successful response has `created: true` and a `key` beginning `jon2_live_`. Save that returned key in Apple Passwords immediately. The raw key is shown only once.

Never add `JON2_MASTER_KEY` to the website or commit it to the repository. If the owner secret is unavailable, stop; do not substitute the personal key.

## Shortcut B — verify the personal key (no owner secret)

1. Add **Ask for Input**, input type **Text**, prompt: `Enter personal Jon2 API key`. Or retrieve the saved personal key from Apple Passwords using an appropriate Passwords action.
2. Add **Get Contents of URL** with URL `https://jon2-ai.jonkabeel.workers.dev/api/keys/verify`.
3. Set Method to **POST**.
4. Leave **Headers empty**. In particular, do not add an Authorization or Bearer header.
5. Set Request Body to **JSON** and add exactly one field:
   - Key: `key`
   - Value: the result of the personal-key input/retrieval action.
6. Run it. A valid key returns `valid: true`.

## Interpreting errors

- `invalid_key`: the value received by the Worker is not a string with the expected `jon2_live_` prefix and length. Check that the JSON value is the actual personal-key text result, not a menu choice, label, or another variable.
- `invalid_or_expired_key`: the key-shaped value was not found as an active, unexpired record in D1, or it was revoked.
- `admin_unauthorized`: the issue/revoke request did not send the owner secret as `Authorization: Bearer <master secret>`.
- HTTP 400 `invalid_json`: the request body is not valid JSON.

Do not paste either secret into support chats or screenshots. Share only the status/error text.

## Scope boundary

Issuing or verifying a key does not make the original Jon2 model ready. It does not enable `/api/chat`, memory, or any other protected operation. No deployment or production configuration is performed by this guide.
