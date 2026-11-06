# Jon2 AI conversation memory

## What it does

- Stores each session's actual user and assistant messages in SQLite.
- Keeps the newest 500 messages per session.
- Reuses the last 8 turns as recent dialogue context, in chronological order.
- Searches up to 200 stored messages for older long-term memories.
- Normalizes Arabic alef variants, ya, diacritics, and tatweel.
- Uses a bounded BM25-style lexical ranker with inverse document frequency,
  document-length normalization, exact-phrase boost, and a small recency boost.
- Excludes the latest 8 turns from long-term retrieval to avoid duplicating
  content already supplied as recent conversation history.
- Supplies at most 4 retrieved snippets to the current chat endpoint.
- Commits each user/assistant exchange atomically only after generation succeeds; failed inference cannot leave an orphan user message in history.
- Provides `GET /api/memory/{session_id}` for message counts and
  `DELETE /api/memory/{session_id}` to erase a session.

This is persistent conversation storage plus lexical retrieval, not a trained
memory neural network, not semantic embeddings, and not a guarantee of factual
recall. It can miss paraphrases that do not share keywords. A retrieved memory
is not proof that the stored statement is true.

## Storage

Set `JON2_MEMORY_DB_PATH` to an absolute writable SQLite file path. If unset,
the default is `~/.jon2-ai/memory.sqlite3`. SQLite uses WAL mode and foreign
keys.

On a machine with a persistent disk, the memory survives process restarts. In
an ephemeral container, the file is lost when the container is replaced;
configure a persistent volume before relying on long-term memory. The public
Git repository and Docker image must never contain the database.

## Single-server website

The Docker image packages the root `index.html` and the FastAPI server.
Opening the API root serves the website from the same origin, so the chat UI
can call `/api/chat` without a second frontend host. GitHub Pages remains a
separate static copy and requires a real API HTTPS URL configured as
`window.JON2_API_BASE_URL` before it can send requests.

## Safety and readiness

- `JON2_CHAT_RELEASE_APPROVED` remains false by default.
- The API continues rejecting chat until the actual original checkpoint is
  loaded and its quality has passed evaluation and human review.
- Memory does not improve model weights or turn a weak checkpoint into a
  capable language model.
- Session UUIDs are identifiers, **not user authentication**. Do not publish
  them or share them with other people.
- Before multi-user public deployment, bind sessions to authenticated owners
  and add rate limits, retention controls, and a clear privacy policy.
- Clear a session from the website's clear-chat action or call the DELETE
  endpoint. Browser-only clearing does not erase the server-side database.
