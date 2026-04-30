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

# Render mounts a persistent disk at /data; the SQLite DB lives there
# so question-log + FAQ store survive deploys. FAIRCLAIMS_STATIC_DIR
# points at the project root inside the image.
ENV FAIRCLAIMS_STATIC_DIR=/app
ENV FAIRCLAIMS_DB_PATH=/data/fairclaims.db

# Render injects $PORT at runtime. Default to 10000 for local docker run.
ENV PORT=10000
EXPOSE 10000

CMD ["sh", "-c", "uvicorn fairclaims_concierge.api.app:create_app --factory --host 0.0.0.0 --port ${PORT}"]
