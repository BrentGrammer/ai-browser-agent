#!/bin/bash
# When HEADLESS=false, run the browser headed on a virtual display and share it
# over VNC (:5900) so the viewer service can stream it to noVNC.
set -e
# Chromium's crash handler needs a writable HOME; the root fs is read-only.
export HOME=/tmp
if [ "${HEADLESS:-true}" = "false" ]; then
  mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix
  Xvfb :99 -screen 0 1440x900x24 &
  export DISPLAY=:99
  x11vnc -display :99 -forever -shared -nopw -quiet -bg
fi
if [ "${LOGIN_MODE:-false}" = "true" ]; then
  exec python open_browser_for_login.py
fi
exec python langgraph_agent.py
