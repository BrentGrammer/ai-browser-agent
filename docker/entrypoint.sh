#!/bin/bash
# When HEADLESS=false, run the browser headed on a virtual display and share it
# over VNC (:5900) so the viewer service can stream it to noVNC.
set -e
if [ "${HEADLESS:-true}" = "false" ]; then
  Xvfb :99 -screen 0 1440x900x24 &
  export DISPLAY=:99
  x11vnc -display :99 -forever -shared -nopw -quiet -bg
fi
if [ "${LOGIN_MODE:-false}" = "true" ]; then
  exec python login.py
fi
exec python langgraph_agent.py
