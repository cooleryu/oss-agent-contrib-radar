from __future__ import annotations

import argparse
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import ROOT, days_since, load_yaml, parse_iso_datetime, read_json, write_json  # noqa: E402


DEFAULT_KEYWORDS = [
    "multi-agent",
    "agent framework",
    "mcp",
    "model context protocol",
    "tool calling",
    "workflow engine",
    "agent runtime",
    "llm harness",
    "eval harness",
    "rag agent",
    "memory agent",
    "browser agent",
    "computer use agent",
    "langgraph",
    "langchain",
    "openai agents",
    "autonomous agent",
    "agent orchestration",
    "agent memory",
    "agent evaluation",
    "tracing agents",
    "llm observability",
    "ai workflow",
    "agentic workflow",
    "ai agent",
    "llm agent",
    "agent",
    "tool",
    "tracing",
    "evals",
    "rag",
]


def combined_text(context: Dict[str, Any]) -> str:
    values = [
        context.get("fullName", ""),
        context.get("description", ""),
        " ".join(context.get("topics") or []),
        context.get("readmeExcerpt", ""),
    ]
    return " ".join(values).lower()


def matched_keywords(context: Dict[str, Any], keywords: Optional[List[str]] = None) -> List[str]:
    text = combined_text(context)
    return sorted({keyword for keyword in (keywords or DEFAULT_KEYWORDS) if keyword.lower() in text})


def date_within(value: Optional[str], days: int, now: datetime) -> bool:
    age = days_since(value, now=now)
    return age is not None and age <= days


def issue_label_names(issue: Dict[str, Any]) -> List[str]:
    labels = issue.get("labels") or []
    return [str(label.get("name", "")).lower() for label in labels if isinstance(label, dict)]


def issue_score(issue: Dict[str, Any]) -> int:
    labels = issue_label_names(issue)
    score = 0
    weights = {
        "bug": 5,
        "good first issue": 5,
        "help wanted": 4,
        "enhancement": 3,
        "test": 3,
        "tests": 3,
        "documentation": 1,
    }
    for label in labels:
        score += weights.get(label, 0)
    comments = issue.get("comments") or 0
    if isinstance(comments, list):
        comment_count = len(comments)
    else:
        comment_count = int(comments or 0)
    score += min(comment_count, 4)
    if not issue.get("assignees"):
        score += 2
    return score


def summarize_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    labels = issue_label_names(issue)
    recommendation = "Maybe"
    if any(label in labels for label in ["bug", "good first issue", "help wanted"]):
        recommendation = "Pick"
    if issue.get("assignees"):
        recommendation = "Skip"
    return {
        "title": issue.get("title"),
        "url": issue.get("url"),
        "labels": labels,
        "maintainerContext": "Use issue comments on GitHub to confirm maintainer intent before editing.",
        "problemSummary": issue.get("title"),
        "whySuitable": "Small enough to inspect locally if it has clear reproduction steps and test coverage.",
        "expectedTechnicalDifficulty": "Medium",
        "requiredFilesToInspect": ["README", "CONTRIBUTING", "tests", "related source files"],
        "reproductionPlan": "Read issue, install project, run relevant tests, reproduce before editing.",
        "testPlan": "Add or update focused tests, then run the project test command and related CI checks locally.",
        "estimatedPrScope": "One focused bugfix or test/devex improvement.",
        "risk": "Skip if reproduction is vague, someone is assigned, or maintainers are debating roadmap.",
        "interviewValue": "Useful if it exercises agent runtime, tool calling, tracing, eval, RAG, or workflow behavior.",
        "recommendation": recommendation,
    }


def hard_filter_reasons(
    context: Dict[str, Any],
    activity: Dict[str, Any],
    now: datetime,
    keywords: Optional[List[str]] = None,
) -> List[str]:
    signals = context.get("signals") or {}
    stars = int(context.get("stars") or 0)
    reasons: List[str] = []
    matches = matched_keywords(context, keywords)
    if context.get("isArchived"):
        reasons.append("archived")
    if context.get("isFork"):
        reasons.append("fork")
    if stars < 500:
        reasons.append("stars_below_500")
    if 500 <= stars < 1000 and not context.get("trending", {}).get("periods"):
        reasons.append("watchlist_stars_without_trending_signal")
    if not signals.get("hasReadme"):
        reasons.append("missing_readme")
    if not signals.get("hasCi"):
        reasons.append("missing_ci")
    if not signals.get("hasTests"):
        reasons.append("missing_tests_or_test_command")
    if not matches:
        reasons.append("not_ai_agent_related")
    if not date_within(activity.get("lastCommitAt"), 7, now):
        reasons.append("no_recent_commit_7d")
    if not date_within(activity.get("lastMergedPrAt"), 7, now):
        reasons.append("no_recent_merged_pr_7d")
    if not date_within(activity.get("lastIssueOrPrUpdatedAt"), 14, now):
        reasons.append("no_recent_issue_or_pr_response_14d")
    if int(activity.get("openPrCount") or 0) > 100 and int(activity.get("recentMergedPrCount7d") or 0) < 3:
        reasons.append("large_open_pr_backlog_low_merge_velocity")
    return reasons


def score_repo(
    context: Dict[str, Any],
    activity: Dict[str, Any],
    now_iso: Optional[str] = None,
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    now = parse_iso_datetime(now_iso) if now_iso else datetime.now(timezone.utc)
    if now is None:
        now = datetime.now(timezone.utc)
    signals = context.get("signals") or {}
    trending = context.get("trending") or {}
    stars = int(context.get("stars") or 0)
    matches = matched_keywords(context, keywords)
    rejection_reasons = hard_filter_reasons(context, activity, now, keywords)

    heat = 0
    heat += 6 if stars >= 1000 else 3 if stars >= 500 else 0
    heat += 4 if stars >= 5000 else 0
    heat += 4 if "weekly" in trending.get("periods", []) else 0
    heat += 4 if "monthly" in trending.get("periods", []) else 0
    heat += min(2, int(trending.get("weeklyStars") or 0) // 250)
    heat = min(20, heat)

    direction = min(20, 4 + len(matches) * 3)
    if any(keyword in matches for keyword in ["agent framework", "tool calling", "agent runtime", "mcp"]):
        direction = min(20, direction + 4)

    maintenance = 0
    maintenance += 6 if date_within(activity.get("lastCommitAt"), 7, now) else 0
    maintenance += 6 if date_within(activity.get("lastMergedPrAt"), 7, now) else 0
    maintenance += 4 if date_within(activity.get("lastIssueOrPrUpdatedAt"), 14, now) else 0
    maintenance += min(4, int(activity.get("recentMergedPrCount7d") or 0))

    contributability = 0
    open_issues = activity.get("openIssues") or []
    if signals.get("hasContributing"):
        contributability += 3
    if signals.get("testCommands"):
        contributability += 3
    if open_issues:
        contributability += 3
    if any(any(label in ["bug", "good first issue", "help wanted", "enhancement"] for label in issue_label_names(issue)) for issue in open_issues):
        contributability += 4
    if int(context.get("openIssuesCount") or 0) > 0:
        contributability += 2
    contributability = min(15, contributability)

    testing_ci = 0
    testing_ci += 4 if signals.get("hasCi") else 0
    testing_ci += 3 if signals.get("hasTests") else 0
    testing_ci += 2 if activity.get("workflowRuns") else 0
    testing_ci += 1 if any((run.get("conclusion") == "success") for run in activity.get("workflowRuns", [])) else 0

    merge_probability = 0
    open_pr_count = int(activity.get("openPrCount") or 0)
    if open_pr_count <= 50:
        merge_probability += 3
    if int(activity.get("recentMergedPrCount7d") or 0) > 0:
        merge_probability += 4
    if any(pr.get("reviewDecision") for pr in activity.get("openPrs", [])):
        merge_probability += 2
    if open_issues:
        merge_probability += 1

    interview_value = min(5, 2 + min(3, len(matches)))

    total = heat + direction + maintenance + contributability + testing_ci + merge_probability + interview_value
    passed = not rejection_reasons
    if not passed:
        recommendation = "Reject"
    elif total >= 85:
        recommendation = "Strong yes"
    elif total >= 70:
        recommendation = "Maybe"
    else:
        recommendation = "Watchlist"

    top_issues = [
        summarize_issue(issue)
        for issue in sorted(open_issues, key=issue_score, reverse=True)[:3]
    ]

    return {
        "repo": context.get("fullName"),
        "url": context.get("url"),
        "stars": stars,
        "forks": context.get("forks"),
        "primaryLanguage": context.get("primaryLanguage"),
        "trending": trending,
        "matchedKeywords": matches,
        "signals": signals,
        "activitySummary": {
            "lastCommitAt": activity.get("lastCommitAt"),
            "lastMergedPrAt": activity.get("lastMergedPrAt"),
            "lastIssueOrPrUpdatedAt": activity.get("lastIssueOrPrUpdatedAt"),
            "recentMergedPrCount7d": activity.get("recentMergedPrCount7d"),
            "openPrCount": activity.get("openPrCount"),
            "workflowRunCountFetched": len(activity.get("workflowRuns") or []),
        },
        "scoreBreakdown": {
            "heatAndGrowth": heat,
            "directionMatch": direction,
            "maintenanceActivity": maintenance,
            "contributability": contributability,
            "testingAndCi": testing_ci,
            "mergeProbability": merge_probability,
            "interviewValue": interview_value,
        },
        "score": total,
        "passedFilters": passed,
        "rejectionReasons": rejection_reasons,
        "recommendation": recommendation,
        "topIssues": top_issues,
        "description": context.get("description"),
        "readmeFilesToStart": [
            "README",
            "CONTRIBUTING",
            ".github/workflows",
            "tests",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply strict filters and score candidate repos.")
    parser.add_argument("--context", required=True)
    parser.add_argument("--activity", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--rejected", required=True)
    args = parser.parse_args()

    keyword_config = load_yaml(ROOT / "configs" / "keywords.yaml")
    keywords = keyword_config.get("keywords") or DEFAULT_KEYWORDS
    contexts = {item["fullName"]: item for item in read_json(Path(args.context), default=[])}
    activities = {item["fullName"]: item for item in read_json(Path(args.activity), default=[])}
    scored = [
        score_repo(context, activities.get(full_name, {}), keywords=keywords)
        for full_name, context in contexts.items()
    ]
    scored.sort(key=lambda item: (item["passedFilters"], item["score"]), reverse=True)
    rejected = [item for item in scored if not item["passedFilters"]]
    write_json(Path(args.output), scored)
    write_json(Path(args.rejected), rejected)
    reason_counts = Counter(reason for item in rejected for reason in item["rejectionReasons"])
    print(f"Wrote {len(scored)} scored repos to {args.output}")
    print(f"Rejected {len(rejected)} repos. Top reasons: {dict(reason_counts.most_common(5))}")


if __name__ == "__main__":
    main()
