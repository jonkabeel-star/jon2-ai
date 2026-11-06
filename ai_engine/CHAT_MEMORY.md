# Jon2 AI conversation memory

## What it does

- Stores each session's actual user and assistant messages in SQLite.
- Keeps the newest 500 messages per session.
- Reuses the last 8 turns as recent dialogue context.
- Searches up to 200 previous messages with a transparent Arabic/English keyword-overlap ranker and supplies up to 2 short matches to the model.
- Provides `GET /api/memory/{session_id}` for message counts and `DELETE /api/memory/{session_id}` to erase a session.
- The browser creates a random UUID session id and stores it locally; the API validates the UUID before accepting it.

This is persistent conversation storage plus lexical retrieval, not a trained memory neural network, not semantic embeddings, and not a guarantee of factual recall. The small original Jon2 checkpoint has a short context window, so only compact snippets can be passed into generation.

## Storage

Set `JON2_MEMORY_DB_PATH` to an absolute writable SQLite file path. If unset, the default is `~/.jon2-ai/memory.sqlite3`. SQLite uses WAL mode and foreign keys.

On a machine with a persistent disk, the memory survives process restarts. In an ephemeral container, the file is lost when the container is replaced; configure a persistent volume before relying on long-term memory. The public Git repository and Docker image must never contain the database.

## Single-server website

The Docker image packages the root `index.html` and the FastAPI server. Opening the API root serves the website from the same origin, so the chat UI can call `/api/chat` without a second frontend host. GitHub Pages remains a separate static copy and requires a real API HTTPS URL configured as `window.JON2_API_BASE_URL` before it can send requests.

## Safety and readiness

- `JON2_CHAT_RELEASE_APPROVED` remains false by default.
- The API continues rejecting chat until the actual original checkpoint is loaded and its quality has passed evaluation and human review.
- Memory does not improve model weights or turn a weak checkpoint into a capable language model.
- Session UUIDs are capability-like identifiers. Do not publish them or share them with other people.
- Clear a session from the website's clear-chat action or call the DELETE endpoint.
