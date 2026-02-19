# 🐜 SWARM - Docker Container
# Rój agentów AI w kontenerze

FROM python:3.11-slim

LABEL maintainer="Karen Tonoyan"
LABEL description="Swarm AI Agents - Multi-agent system"

# Zmienne środowiskowe
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Katalog roboczy
WORKDIR /app

# Zainstaluj zależności systemowe
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Skopiuj requirements
COPY requirements.txt .

# Zainstaluj zależności Python
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Skopiuj kod
COPY . .

# Port dla API
EXPOSE 8765

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# Uruchom rój
CMD ["python", "-m", "swarm.swarm_manager"]
