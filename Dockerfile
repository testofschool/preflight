FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg=7:7.1.5-0+deb13u1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-cloud.lock /app/requirements-cloud.lock
RUN pip install --no-cache-dir -r /app/requirements-cloud.lock
COPY app.py /app/app.py
COPY preflight_core /app/preflight_core
COPY cloud /app/cloud
COPY static /app/static
COPY artifacts/engine.json artifacts/vectorizer.joblib artifacts/prompt_vectors.npz /app/artifacts/
RUN useradd --create-home --uid 10001 appuser
USER appuser
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
