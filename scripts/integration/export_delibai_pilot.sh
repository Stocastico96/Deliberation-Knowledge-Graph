#!/usr/bin/env bash
# Export the DelibAI pilot tables (Your Priorities research fork, PostgreSQL)
# as JSON files, one per table, for scripts/integration/import_delibai.py.
#
# Read-only. Uses the running "deliberative-postgres" container by default.
# Usage:
#   scripts/integration/export_delibai_pilot.sh [OUTPUT_DIR]
# Environment overrides:
#   DELIBAI_PG_CONTAINER (default deliberative-postgres)
#   DELIBAI_PG_USER      (default postgres)
#   DELIBAI_PG_DB        (default your_priorities_dev)
#
# The output directory contains password material inside pilot_participants
# (metadata column). Keep it outside the repository; the importer never copies
# that column into the graph.
set -euo pipefail

OUT_DIR="${1:-/home/svagnoni/delibai_analysis/dkg_export}"
CONTAINER="${DELIBAI_PG_CONTAINER:-deliberative-postgres}"
PG_USER="${DELIBAI_PG_USER:-postgres}"
PG_DB="${DELIBAI_PG_DB:-your_priorities_dev}"

mkdir -p "$OUT_DIR"
chmod 700 "$OUT_DIR"

for table in pilot_participants pilot_task_responses pilot_peer_flags pilot_events pilot_survey_responses; do
  docker exec "$CONTAINER" psql -U "$PG_USER" -d "$PG_DB" -At \
    -c "select coalesce(json_agg(row_to_json(t)),'[]') from (select * from ${table} order by id) t" \
    > "$OUT_DIR/${table}.json"
  printf '%-24s %s rows\n' "$table" "$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$OUT_DIR/${table}.json")"
done

date -u +%Y-%m-%dT%H:%M:%SZ > "$OUT_DIR/snapshot_date.txt"
echo "snapshot written to $OUT_DIR ($(cat "$OUT_DIR/snapshot_date.txt"))"
