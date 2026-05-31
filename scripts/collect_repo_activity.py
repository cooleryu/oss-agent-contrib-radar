from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import (  # noqa: E402
    CommandError,
    ROOT,
    RateLimitExceeded,
    check_rate_limit_or_exit,
    days_since,
    load_yaml,
    max_iso,
    read_json,
    run_gh_json,
    write_json,
)


def safe_gh_json(args: List[str], fallback: Any) -> Any:
    try:
        return run_gh_json(args)
    except RateLimitExceeded:
        raise
    except CommandError:
        return fallback


def list_issues(repo: str, state: str) -> List[Dict[str, Any]]:
    return safe_gh_json(
        [
            "issue",
            "list",
            "-R",
            repo,
            "--state",
            state,
            "--limit",
            "20",
            "--json",
            "number,title,url,labels,createdAt,updatedAt,author,comments,assignees",
        ],
        fallback=[],
    )


def list_prs(repo: str, state: str) -> List[Dict[str, Any]]:
    return safe_gh_json(
        [
            "pr",
            "list",
            "-R",
            repo,
            "--state",
            state,
            "--limit",
            "20",
            "--json",
            "number,title,url,labels,createdAt,updatedAt,author,assignees,isDraft,reviewDecision,mergedAt,closedAt",
        ],
        fallback=[],
    )


def collect_activity_for_repo(repo: str) -> Dict[str, Any]:
    commits = safe_gh_json(["api", f"repos/{repo}/commits?per_page=30"], fallback=[])
    open_issues = list_issues(repo, "open")
    closed_issues = list_issues(repo, "closed")
    open_prs = list_prs(repo, "open")
    merged_prs = list_prs(repo, "merged")
    closed_prs = list_prs(repo, "closed")
    workflow_payload = safe_gh_json(["api", f"repos/{repo}/actions/runs?per_page=10"], fallback={})
    workflow_runs = workflow_payload.get("workflow_runs", []) if isinstance(workflow_payload, dict) else []

    last_commit_at = None
    if commits:
        last_commit_at = commits[0].get("commit", {}).get("committer", {}).get("date")

    last_merged_pr_at = max_iso([pr.get("mergedAt") for pr in merged_prs])
    last_issue_or_pr_updated_at = max_iso(
        [issue.get("updatedAt") for issue in open_issues + closed_issues]
        + [pr.get("updatedAt") for pr in open_prs + merged_prs + closed_prs]
    )
    now = datetime.now(timezone.utc)
    recent_merged_pr_count_7d = sum(
        1 for pr in merged_prs if (days_since(pr.get("mergedAt"), now=now) or 999) <= 7
    )

    return {
        "fullName": repo,
        "lastCommitAt": last_commit_at,
        "lastMergedPrAt": last_merged_pr_at,
        "lastIssueOrPrUpdatedAt": last_issue_or_pr_updated_at,
        "recentMergedPrCount7d": recent_merged_pr_count_7d,
        "commitCountFetched": len(commits),
        "openIssueCountFetched": len(open_issues),
        "closedIssueCountFetched": len(closed_issues),
        "openPrCount": len(open_prs),
        "mergedPrCountFetched": len(merged_prs),
        "closedPrCountFetched": len(closed_prs),
        "openIssues": open_issues,
        "closedIssues": closed_issues,
        "openPrs": open_prs,
        "mergedPrs": merged_prs,
        "closedPrs": closed_prs,
        "workflowRuns": [
            {
                "name": run.get("name"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "createdAt": run.get("created_at"),
                "updatedAt": run.get("updated_at"),
                "htmlUrl": run.get("html_url"),
            }
            for run in workflow_runs[:10]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect recent repo activity.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-repos", type=int, default=25)
    parser.add_argument("--sleep-seconds", type=float, default=0.5)
    args = parser.parse_args()

    config = load_yaml(ROOT / "configs" / "strict_filters.yaml")
    check_rate_limit_or_exit(config)
    contexts = read_json(Path(args.input), default=[])
    activities: List[Dict[str, Any]] = []
    for index, context in enumerate(contexts[: args.max_repos], start=1):
        if index == 1 or index % 5 == 0:
            check_rate_limit_or_exit(config)
        repo = context["fullName"]
        activities.append(collect_activity_for_repo(repo))
        print(f"Collected activity for {repo}")
        if args.sleep_seconds:
            time.sleep(args.sleep_seconds)
    write_json(Path(args.output), activities)
    print(f"Wrote {len(activities)} repo activity records to {args.output}")


if __name__ == "__main__":
    main()
