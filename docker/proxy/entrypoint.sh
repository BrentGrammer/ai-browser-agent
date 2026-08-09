#!/bin/sh
# Tinyproxy config that default-denies all egress except the derived allowlist:
# TARGET_URL's host + LLM_API_DOMAIN + optional extras (subdomains included).
set -eu
: "${TARGET_URL:?Set TARGET_URL to the app the agent operates on}"
: "${LLM_API_DOMAIN:?Set LLM_API_DOMAIN to your LLM provider's API host}"

target_host=$(printf '%s' "$TARGET_URL" \
  | sed -E 's#^[A-Za-z][A-Za-z0-9+.-]*://##; s#/.*$##; s#^[^@]*@##; s#:[0-9]+$##')
ALLOWED_DOMAINS="$target_host,$LLM_API_DOMAIN,${ALLOWED_NAV_DOMAINS:-},${PROXY_EXTRA_ALLOWED_DOMAINS:-}"

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
