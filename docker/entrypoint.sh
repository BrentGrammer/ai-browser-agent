#!/bin/bash
# When HEADLESS=false, run the browser headed on a virtual display and share it
# over VNC (:5900) so the viewer service can stream it to noVNC.
set -e
# DISPLAY and HOME (Chromium's crash handler needs a writable one) come from
# the compose environment so `docker compose exec` sees them too.
if [ "${HEADLESS:-true}" = "false" ]; then
  mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
  Xvfb :99 -screen 0 1440x900x24 &
  # Wait for the display before starting x11vnc, or it races Xvfb and dies.
  for _ in $(seq 1 50); do [ -S /tmp/.X11-unix/X99 ] && break; sleep 0.2; done
  x11vnc -display :99 -forever -shared -nopw -quiet -bg
fi
# Idle until `./agent login` or `./agent run` starts a script.
exec sleep infinity
