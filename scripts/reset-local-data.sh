#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
database="$project_dir/backend/data/ember_finance.db"

if [[ "${1:-}" != "--yes" ]]; then
  echo "This permanently removes Ember's imported spreadsheet data and net-worth history."
  read -r -p "Type RESET to continue: " answer
  [[ "$answer" == "RESET" ]] || { echo "Cancelled."; exit 1; }
fi

if [[ -f "$database" ]]; then
  rm "$database"
  echo "Removed $database. Ember will create a clean database next time it starts."
else
  echo "No local Ember database exists. The app is already clean."
fi
