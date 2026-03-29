#!/usr/bin/with-contenv bashio
set -e

bashio::log.info "Starting HACPM - Home Assistant Chores, Plants & Maintenance"

# Read options from HA add-on config
export HACPM_LOG_LEVEL=$(bashio::config 'log_level')
export HACPM_REALTIME_SYNC=$(bashio::config 'realtime_sync')
export HACPM_POINTS_LOW=$(bashio::config 'default_points.low')
export HACPM_POINTS_MEDIUM=$(bashio::config 'default_points.medium')
export HACPM_POINTS_HIGH=$(bashio::config 'default_points.high')
export HACPM_POINTS_CRITICAL=$(bashio::config 'default_points.critical')

# HA Supervisor token for API calls
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"
export HACPM_DB_PATH="/data/db/hacpm.sqlite"
export HACPM_PHOTOS_PATH="/data/photos"
export HACPM_INGRESS_PATH=$(bashio::addon.ingress_entry)

# Ensure data directories exist
mkdir -p /data/db /data/photos

bashio::log.info "Log level: ${HACPM_LOG_LEVEL}"
bashio::log.info "Ingress path: ${HACPM_INGRESS_PATH}"

cd /app

exec python3 -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8099 \
    --log-level "${HACPM_LOG_LEVEL}"
