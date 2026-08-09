# Playwright image tag must match the playwright version installed below.
FROM mcr.microsoft.com/playwright/python:v1.62.1-noble

WORKDIR /app

COPY langgraph/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt "playwright==1.62.1"

COPY langgraph/ /app/

# Writable dirs for the browser profile, screenshots, and learned knowledge.
RUN mkdir -p /data/profile /data/screenshots /data/knowledge \
    && chown -R pwuser:pwuser /data /app

USER pwuser

CMD ["python", "langgraph_agent.py"]
