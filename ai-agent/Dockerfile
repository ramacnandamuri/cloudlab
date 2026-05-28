# Stage 1 - Builder
FROM python:3.12-slim AS builder

WORKDIR /ai-agent
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --target=/ai-agent/packages \
    -r requirements.txt

# Stage 2 - Hardened runtime
FROM python:3.12-slim

# Remove unnecessary packages
RUN apt-get update && \
    apt-get remove -y perl && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /ai-agent

COPY --from=builder /ai-agent/packages /ai-agent/packages
COPY src/ /ai-agent/src/

ENV PYTHONPATH=/ai-agent/packages

CMD ["python", "-m", "src.agent"]