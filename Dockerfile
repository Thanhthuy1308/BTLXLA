# Production image for the analysis server (deployed on Render, see render.yaml).
#
# Stage 1 builds the React interface so the server also works on its own;
# stage 2 runs the Flask API and that interface with gunicorn on $PORT.

FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build


FROM python:3.11-slim
# PORT is overridden by the hosting platform; WEB_CONCURRENCY is read by gunicorn.
# One worker keeps memory within the 512 MB of Render's free instance.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    PORT=8000 \
    WEB_CONCURRENCY=1 \
    FLASK_DEBUG=0 \
    RUNTIME_TTL_HOURS=6

# The GitHub Pages site that calls this API. Override with an environment
# variable (comma-separated) when the interface is hosted elsewhere.
ENV ALLOWED_ORIGINS=https://thanhthuy1308.github.io

# opencv-python needs these shared libraries even when no window is opened.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 user
WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir . "gunicorn>=23"

COPY web/app.py web/app.py
COPY --from=frontend /app/frontend/dist frontend/dist
RUN mkdir -p web/runtime && chown -R user:user /app/web/runtime

USER user
EXPOSE 8000

# Sync workers: matplotlib's pyplot is not thread-safe, so each worker handles one
# request at a time. The long timeout covers large images on a cold, shared CPU.
CMD gunicorn --bind 0.0.0.0:${PORT} --timeout 180 --access-logfile - web.app:app
