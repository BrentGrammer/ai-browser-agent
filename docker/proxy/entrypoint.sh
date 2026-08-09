#!/bin/sh
# Generates a tinyproxy config whose domain filter default-denies everything
# except ALLOWED_DOMAINS (comma-separated; subdomains of each are allowed).
set -eu
: "${ALLOWED_DOMAINS:?Set ALLOWED_DOMAINS to a comma-separated list of hostnames}"

FILTER=/etc/tinyproxy/filter
: > "$FILTER"
IFS=','
for d in $ALLOWED_DOMAINS; do
  d=$(printf '%s' "$d" | tr -d ' ')
  [ -z "$d" ] && continue
  escaped=$(printf '%s' "$d" | sed 's/\./\\./g')
  printf '^(.+\\.)?%s$\n' "$escaped" >> "$FILTER"
done
unset IFS

cat > /etc/tinyproxy/tinyproxy.conf <<EOF
User tinyproxy
Group tinyproxy
Port 8888
Timeout 600
MaxClients 32
Allow 0.0.0.0/0
ConnectPort 443
Filter $FILTER
FilterExtended On
FilterURLs Off
FilterDefaultDeny Yes
LogLevel Notice
EOF

echo "Egress allowlist:"
cat "$FILTER"
exec tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf
