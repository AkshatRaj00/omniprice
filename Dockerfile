FROM python:3.11-slim-bookworm

# Anti-Root Jail: Run as non-privileged user
RUN groupadd -g 10001 appgroup &&     useradd -u 10000 -g appgroup -s /sbin/nologin -m appuser

WORKDIR /app

# Install security patches & build deps
RUN apt-get update &&     apt-get upgrade -y &&     apt-get install -y --no-install-recommends ca-certificates gcc libc6-dev &&     rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Secure data volume setup
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--no-server-header"]
