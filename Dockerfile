FROM python:3.11-slim

WORKDIR /app

# Install backend (editable not needed in container — copy source and pip install).
COPY backend/pyproject.toml /app/backend/pyproject.toml
COPY backend/src /app/backend/src
RUN pip install --no-cache-dir /app/backend

# Static site assets — served by FastAPI at the same origin as /concierge/ask.
COPY index.html /app/index.html
COPY css /app/css
COPY js /app/js
COPY pages /app/pages

# Seed FAQs + system prompt — read at runtime.
COPY backend/seed /app/backend/seed
COPY backend/prompts /app/backend/prompts

# SQLite path. Free Render tier has no persistent disk, so we default
# to /tmp (ephemeral). On paid tiers with a disk mount, override to
# /data/fairclaims.db via render.yaml.
ENV FAIRCLAIMS_STATIC_DIR=/app
ENV FAIRCLAIMS_DB_PATH=/tmp/fairclaims.db

# Render injects $PORT at runtime. Default to 10000 for local docker run.
ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "uvicorn fairclaims_concierge.api.app:create_app --factory --host 0.0.0.0 --port ${PORT}"]
