# Playwright image tag must match the playwright version installed below.
FROM mcr.microsoft.com/playwright/python:v1.62.1-noble

WORKDIR /app

# Xvfb + x11vnc so the headed browser can be watched via the noVNC viewer service.
RUN apt-get update \
    && apt-get install -y --no-install-recommends xvfb x11vnc \
    && rm -rf /var/lib/apt/lists/*

COPY langgraph/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "playwright==1.62.1"

# Install the provider integration for LLM_MODEL, e.g. openai:gpt-4o -> langchain-openai.
ARG LLM_MODEL
RUN pip install --no-cache-dir "langchain-$(echo "${LLM_MODEL%%:*}" | tr _ -)"

COPY langgraph/ /app/
COPY docker/entrypoint.sh /entrypoint.sh

# Writable dirs for the browser profile, screenshots, and learned knowledge.
RUN chmod +x /entrypoint.sh \
    && mkdir -p /data/profile /data/screenshots /data/knowledge \
    && chown -R pwuser:pwuser /data /app

USER pwuser

ENTRYPOINT ["/entrypoint.sh"]
