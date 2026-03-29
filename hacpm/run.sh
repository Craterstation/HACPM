#!/usr/bin/env bash
set -e

CONFIG_PATH=/data/options.json

echo "Starting HACPM - Home Assistant Chores, Plants & Maintenance"

# Read options from HA add-on config (using jq instead of bashio)
export HACPM_LOG_LEVEL=$(jq -r '.log_level // "info"' "$CONFIG_PATH")
export HACPM_REALTIME_SYNC=$(jq -r '.realtime_sync // true' "$CONFIG_PATH")
export HACPM_POINTS_LOW=$(jq -r '.default_points.low // 1' "$CONFIG_PATH")
export HACPM_POINTS_MEDIUM=$(jq -r '.default_points.medium // 3' "$CONFIG_PATH")
export HACPM_POINTS_HIGH=$(jq -r '.default_points.high // 5' "$CONFIG_PATH")
export HACPM_POINTS_CRITICAL=$(jq -r '.default_points.critical // 10' "$CONFIG_PATH")

# HA Supervisor token for API calls
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"
export HACPM_DB_PATH="/data/db/hacpm.sqlite"
export HACPM_PHOTOS_PATH="/data/photos"

# Get ingress entry from supervisor API
if [ -n "$SUPERVISOR_TOKEN" ]; then
    INGRESS_ENTRY=$(curl -s -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
        http://supervisor/addons/self/info 2>/dev/null | jq -r '.data.ingress_entry // ""' 2>/dev/null || echo "")
    export HACPM_INGRESS_PATH="${INGRESS_ENTRY}"
else
    export HACPM_INGRESS_PATH=""
fi

# Ensure data directories exist
mkdir -p /data/db /data/photos

echo "Log level: ${HACPM_LOG_LEVEL}"
echo "Ingress path: ${HACPM_INGRESS_PATH}"

cd /app

exec python3 -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8099 \
    --log-level "${HACPM_LOG_LEVEL}"
