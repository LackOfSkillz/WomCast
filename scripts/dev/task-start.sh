#!/usr/bin/env bash
set -euo pipefail
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PATH_JSON="docs/spec/TASKS.json"
[ -f "$PATH_JSON" ] || { echo "No TASKS.json yet"; exit 0; }
jq --arg ts "$TS" '
  .tasks |= map(
    if (.id as $id | (env.IDS // "") | split(",") | index($id)) and (.start_at_utc == null or .start_at_utc == "")
    then .start_at_utc=$ts | .status="in_progress" else . end )' "$PATH_JSON" > "$PATH_JSON.tmp" && mv "$PATH_JSON.tmp" "$PATH_JSON"