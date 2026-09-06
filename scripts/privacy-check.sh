#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_dir"

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ "$repo_root" != "$project_dir" ]]; then
  echo "Privacy check stopped: initialize Git inside $project_dir first." >&2
  exit 1
fi

blocked="$(git ls-files | grep -Ei '(^|/)(backend/data|statements|imports|backups|private)/|\.(db|sqlite3?|pdf|ofx|qfx|qbo)$|(^|/)\.env($|\.)' | grep -vE '(^|/)\.env\.example$' || true)"
if [[ -n "$blocked" ]]; then
  echo "Privacy check failed. Private-looking files are tracked:" >&2
  echo "$blocked" >&2
  exit 1
fi

if git grep -nF "$HOME/" -- ':!package-lock.json' >/dev/null 2>&1; then
  echo "Privacy check failed. A tracked file contains an absolute home-directory path:" >&2
  git grep -nF "$HOME/" -- ':!package-lock.json' >&2
  exit 1
fi

if git grep -nE '[0-9]{12,19}' -- app backend scripts README.md CONTRIBUTING.md >/dev/null 2>&1; then
  echo "Privacy check failed. Review this possible full account/card number:" >&2
  git grep -nE '[0-9]{12,19}' -- app backend scripts README.md CONTRIBUTING.md >&2
  exit 1
fi

echo "Privacy check passed: no tracked databases, statements, secrets, home paths, or long account-number patterns."
