FROM python:3.11.9-slim

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd --uid 1000 --create-home voiceflow
WORKDIR /app

# Copy only backend source
COPY --chown=voiceflow:voiceflow . .

USER voiceflow

# Install server-mode dependencies
RUN pip install --no-cache-dir -e ".[server]"

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

CMD ["uvicorn", "voiceflow.main:app", "--host", "0.0.0.0", "--port", "8765"]
