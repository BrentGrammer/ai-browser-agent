FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends novnc websockify \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 6080
CMD ["websockify", "--web", "/usr/share/novnc", "6080", "agent:5900"]
