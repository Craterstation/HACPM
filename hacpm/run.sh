#!/usr/bin/env bashrc
set -e

echo "Starting HACPM - Home Assistant Chores, Plants & Maintenance"

# Read options from HA add-on config
export HACPM_LOG_LEVEL=$(bashio::config 'log_level' 'info')
export HACPM_REALTIME_SYNC=$(bashio::config 'realtime_sync' 'true')
export HACPM_POINTS_LOW=$(bashio::config 'default_points.low' '1')
export HACPM_POINTS_MEDIUM=$(bashio::config 'default_points.medium' '3')
export HACPM_POINTS_HIGH=$(bashio::config 'default_points.high' '5')
export HACPM_POINTS_CRITICAL=$(bashio::config 'default_points.critical' '10')

# HA Supervisor token for API calls
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"
export HACPM_DB_PATH="/data/db/hacpm.sqlite"
export HACPM_PHOTOS_PATH="/data/photos"
export HACPM_INGRESS_PATH=$(bashio::addon.ingress_entry)

echo "Log level: ${HACPM_LOG_LEVEL}"
echo "Realtime sync: ${HACPM_REALTIME_SYNC}"
echo "Ingress path: ${HACPM_INGRESS_PATH}"

cd /app

exec python3 -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8099 \
    --log-level "${HACPM_LOG_LEVEL}"
