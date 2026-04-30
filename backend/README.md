# FairClaims Concierge — backend

FAQ-grounded chat for `fairclaims.us`. FastAPI + SQLite + Groq.

## Local dev

1. Create `backend/.env` from `backend/.env.example`. Set `FAIRCLAIMS_LLM_BACKEND=mock` for no-LLM dev, or `FAIRCLAIMS_LLM_BACKEND=api` with a Groq key to test live LLM.
2. From the repo root:
   ```
   pip install -e ./backend[dev]
   pytest backend/tests -v
   FAIRCLAIMS_DB_PATH=./data/fairclaims.db FAIRCLAIMS_LOG_RENDERER=console FAIRCLAIMS_STATIC_DIR=. \
     uvicorn fairclaims_concierge.api.app:create_app --factory --port 8000
   ```
3. Open `http://localhost:8000/` — bubble appears bottom-right on every page.

## Endpoints

- `POST /concierge/ask` — public; body `{question, page_url?}` → `ConciergeResponse`.
- `GET /admin/questions/unmatched?since=…&limit=…` — bearer-token gated.
- `GET /admin/questions/digest?days=…` — bearer-token gated.
- `GET /health` — uptime probe.

## Env vars

See `backend/.env.example` for the full list and `render.yaml` for the production wiring. All env vars use the `FAIRCLAIMS_` prefix.

## Question log

Every `/concierge/ask` call writes one row to `questions_log` (PII-scrubbed question, top FAQ, matched flag, weekly-rotated visitor hash, page URL, UA bucket). Read it with the admin endpoints or by SSHing into the Render shell:

```
sqlite3 /data/fairclaims.db "SELECT asked_at, matched, top_faq_score, question FROM questions_log ORDER BY id DESC LIMIT 20;"
```

## Kill switch

`FAIRCLAIMS_CONCIERGE_ENABLED=false` (no redeploy needed) — `/concierge/ask` returns 503; widget shows the offline message but bubble still mounts. Set back to `true` to re-enable.

## Lifted from CEN

`backend/src/fairclaims_concierge/` is duplicated from CEN's `src/cen/` concierge slice (FAQ store, retriever, scrubber, prompt assembly, openai_compat client). Future improvements port by hand. Workflow / case / SOP / chat-history surfaces are not lifted.
