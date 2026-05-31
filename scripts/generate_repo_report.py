from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import read_json  # noqa: E402


def format_issue(issue: Dict[str, Any]) -> str:
    if not issue:
        return "暂无合适 issue，需要人工继续看。"
    labels = ", ".join(issue.get("labels") or []) or "no labels"
    return f"[{issue.get('title')}]({issue.get('url')}) - {labels} - {issue.get('recommendation')}"


def report_lines(scored: List[Dict[str, Any]], rejected: List[Dict[str, Any]]) -> List[str]:
    passed = [item for item in scored if item.get("passedFilters")]
    stars_1000 = [item for item in scored if int(item.get("stars") or 0) >= 1000]
    stars_500_999 = [
        item for item in scored if 500 <= int(item.get("stars") or 0) < 1000
    ]
    reason_counts = Counter(reason for item in rejected for reason in item.get("rejectionReasons", []))

    lines: List[str] = []
    lines.append("# Weekly OSS Agent Contribution Radar")
    lines.append("")
    lines.append("## Contribution Ethics")
    lines.append("")
    lines.append("This report is not a PR farming queue. It is a strict triage artifact.")
    lines.append("")
    lines.append("Default behavior:")
    lines.append("")
    lines.append("1. Reject typo-only, formatting-only, cosmetic-only, or profile-decoration opportunities.")
    lines.append("2. Reject issues without repo context, reproduction path, test plan, and collision check.")
    lines.append("3. Prefer zero recommendations over low-quality recommendations.")
    lines.append("4. Spend automation and AI tokens to protect maintainer review time.")
    lines.append("5. Require human review before any final PR submission.")
    lines.append("")
    lines.append("## Strict Filters")
    lines.append("")
    for index, item in enumerate(
        [
            "stars >= 1000 优先。",
            "stars 500 到 999 仅进入观察池，且需要 Trending 信号。",
            "stars < 500 排除。",
            "增长信号优先使用 GitHub Trending daily / weekly / monthly。",
            "最近 7 天必须有 commit。",
            "最近 7 天必须有 PR 合并。",
            "最近 14 天必须有 issue 或 PR 更新信号。",
            "必须有 CI。",
            "必须有测试目录或明确测试命令。",
            "必须和 AI Agent / LLM 工程方向相关。",
        ],
        start=1,
    ):
        lines.append(f"{index}. {item}")

    lines.append("")
    lines.append("## Search Summary")
    lines.append("")
    lines.append(f"1. 原始仓库数量：{len(scored)}")
    lines.append(f"2. stars >= 1000 数量：{len(stars_1000)}")
    lines.append(f"3. stars 500 到 999 数量：{len(stars_500_999)}")
    lines.append(f"4. 硬过滤后剩余数量：{len(passed)}")
    lines.append(f"5. 排除数量：{len(rejected)}")
    lines.append("6. Top rejection reasons：")
    if reason_counts:
        for reason, count in reason_counts.most_common(10):
            lines.append(f"   - {reason}: {count}")
    else:
        lines.append("   - 无")

    lines.append("")
    lines.append("## Top Candidates")
    lines.append("")
    for item in scored[:10]:
        activity = item.get("activitySummary") or {}
        breakdown = item.get("scoreBreakdown") or {}
        top_issue = item.get("topIssues", [{}])[0] if item.get("topIssues") else {}
        lines.append(f"### {item.get('repo')}")
        lines.append("")
        lines.append(f"1. URL: {item.get('url')}")
        lines.append(f"2. Stars: {item.get('stars')}")
        lines.append(f"3. Recent growth signal: {item.get('trending')}")
        lines.append(
            f"4. Recent activity: commit={activity.get('lastCommitAt')}, "
            f"merged_pr={activity.get('lastMergedPrAt')}, "
            f"issue_or_pr_update={activity.get('lastIssueOrPrUpdatedAt')}"
        )
        lines.append(f"5. Main language: {item.get('primaryLanguage')}")
        lines.append(f"6. AI Agent match: {', '.join(item.get('matchedKeywords') or [])}")
        lines.append(f"7. Testing / CI: {item.get('signals')}")
        lines.append(f"8. Score: {item.get('score')} / 100")
        lines.append(f"9. Score breakdown: {breakdown}")
        lines.append(f"10. Recommendation: {item.get('recommendation')}")
        if item.get("rejectionReasons"):
            lines.append(f"11. Rejection reason: {', '.join(item.get('rejectionReasons') or [])}")
        else:
            lines.append("11. Rejection reason: none")
        lines.append(f"12. 最值得先看的 issue: {format_issue(top_issue)}")
        lines.append(
            "13. 面试叙事价值: "
            "可从项目定位、Agent/LLM 工程问题、复现过程、测试方案和维护者接受理由展开。"
        )
        lines.append("")

    lines.append("## Top 3 Recommended Repos")
    lines.append("")
    if not passed:
        lines.append("本轮没有仓库通过全部硬过滤。建议扩大 Trending 周期或降低部分时间窗口后再跑。")
    for item in passed[:3]:
        top_issue = item.get("topIssues", [{}])[0] if item.get("topIssues") else {}
        lines.append(f"### {item.get('repo')}")
        lines.append("")
        lines.append(f"1. 推荐理由: score={item.get('score')}，匹配 {', '.join(item.get('matchedKeywords') or [])}")
        lines.append("2. 最大风险: 需要人工确认 issue 上下文和维护者真实态度。")
        lines.append(f"3. 最适合贡献切入点: {format_issue(top_issue)}")
        lines.append("4. 面试叙事角度: 展示你如何筛选活跃 Agent 工程项目，并用测试驱动小范围修复。")
        lines.append("5. 预计反馈速度: 参考最近 merged PR 和 issue/PR 更新时间。")
        lines.append("6. 最适合先读的文件: README, CONTRIBUTING, CI workflow, tests。")
        lines.append(f"7. 最适合先看的 issue / PR: {format_issue(top_issue)}")
        lines.append("")

    lines.append("## Rejected Repos")
    lines.append("")
    for item in rejected[:50]:
        watch = "是" if int(item.get("stars") or 0) >= 500 and item.get("trending", {}).get("periods") else "否"
        lines.append(f"- {item.get('repo')} - {item.get('url')} - {', '.join(item.get('rejectionReasons') or [])} - 未来观察: {watch}")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly markdown report.")
    parser.add_argument("--scored", required=True)
    parser.add_argument("--rejected", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    scored = read_json(Path(args.scored), default=[])
    rejected = read_json(Path(args.rejected), default=[])
    lines = report_lines(scored, rejected)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote report to {output_path}")


if __name__ == "__main__":
    main()
