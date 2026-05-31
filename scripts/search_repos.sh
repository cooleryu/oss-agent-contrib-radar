#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MAX_REPOS="${MAX_REPOS:-25}"
ACTIVITY_MAX_REPOS="${ACTIVITY_MAX_REPOS:-$MAX_REPOS}"
TRENDING_SLEEP_SECONDS="${TRENDING_SLEEP_SECONDS:-1}"
API_SLEEP_SECONDS="${API_SLEEP_SECONDS:-0.5}"
SINCE_VALUES="${SINCE_VALUES:-daily weekly monthly}"
LANGUAGES="${LANGUAGES:-All Python TypeScript Java Go Rust}"
SKIP_FETCH=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-fetch)
      SKIP_FETCH=1
      shift
      ;;
    --max-repos)
      MAX_REPOS="$2"
      ACTIVITY_MAX_REPOS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p outputs/raw outputs/candidates outputs/rejected outputs/reports workspace/repos

python3 scripts/collect_repo_context.py check-rate-limit

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr ' /+' '___'
}

if [ "$SKIP_FETCH" -eq 0 ]; then
  for since in $SINCE_VALUES; do
    for language in $LANGUAGES; do
      slug="$(slugify "$language")"
      out="outputs/raw/trending_${since}_${slug}.html"
      if [ "$language" = "All" ]; then
        url="https://github.com/trending?since=${since}"
      else
        url="https://github.com/trending/${language}?since=${since}"
      fi
      echo "Fetching $url"
      curl --retry 3 --retry-delay 2 --retry-all-errors --connect-timeout 20 \
        -fsSL -A "oss-agent-contrib-radar/0.1" "$url" -o "$out"
      sleep "$TRENDING_SLEEP_SECONDS"
    done
  done
fi

python3 scripts/collect_repo_context.py parse-trending \
  --raw-dir outputs/raw \
  --out outputs/candidates/trending_repos.json

python3 scripts/collect_repo_context.py enrich \
  --input outputs/candidates/trending_repos.json \
  --output outputs/candidates/repo_context.json \
  --max-repos "$MAX_REPOS" \
  --sleep-seconds "$API_SLEEP_SECONDS"

python3 scripts/collect_repo_activity.py \
  --input outputs/candidates/repo_context.json \
  --output outputs/candidates/repo_activity.json \
  --max-repos "$ACTIVITY_MAX_REPOS" \
  --sleep-seconds "$API_SLEEP_SECONDS"

python3 scripts/score_repos.py \
  --context outputs/candidates/repo_context.json \
  --activity outputs/candidates/repo_activity.json \
  --output outputs/candidates/scored_repos.json \
  --rejected outputs/rejected/rejected_repos.json

python3 scripts/generate_repo_report.py \
  --scored outputs/candidates/scored_repos.json \
  --rejected outputs/rejected/rejected_repos.json \
  --output outputs/weekly_report.md

echo "Report: $ROOT_DIR/outputs/weekly_report.md"
