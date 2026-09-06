#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"
./scripts/privacy-check.sh

version="${1:-local}"
archive="ember-finance-${version}.zip"
git archive --format=zip --output="$archive" HEAD
echo "Created $archive from tracked source only."
