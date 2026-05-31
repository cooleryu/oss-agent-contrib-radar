#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INDEX_FILE="${1:-"$ROOT_DIR/outputs/contributions/submitted_prs.tsv"}"

if [[ ! -f "$INDEX_FILE" ]]; then
  echo "Missing PR index: $INDEX_FILE" >&2
  exit 1
fi

tail -n +2 "$INDEX_FILE" | while IFS=$'\t' read -r slug repo pr issue branch local_dir; do
  [[ -z "${slug:-}" ]] && continue

  echo "== $slug =="
  echo "repo: $repo"
  echo "pr: #$pr"
  echo "issue: #$issue"
  echo "branch: $branch"
  echo "local: $local_dir"

  gh pr view "$pr" \
    --repo "$repo" \
    --json number,title,url,state,isDraft,mergeStateStatus,reviewDecision,updatedAt \
    --template 'title: {{.title}}
url: {{.url}}
state: {{.state}} draft={{.isDraft}} merge={{.mergeStateStatus}} review={{.reviewDecision}}
updated: {{.updatedAt}}
'

  echo "checks:"
  gh pr checks "$pr" --repo "$repo" || true
  echo
done
