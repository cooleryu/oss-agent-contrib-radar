# oss-agent-contrib-radar

本地开源贡献机会筛选工具，目标是严苛筛选 AI Agent / LLM 工程方向中值得投入的 GitHub 仓库，并输出可人工 review 的候选报告。

第一版只做筛选和报告：

1. 不 fork。
2. 不 clone 第三方仓库。
3. 不创建 issue / PR / comment。
4. 不修改第三方仓库代码。
5. 遇到 GitHub API 限流或低预算立即停止。

## 为什么先用 Trending

GitHub Search API 有单独限制，`search` 额度通常是每分钟 30 次，`code_search` 更低。这个项目第一版把 GitHub Trending 作为增长信号来源，减少 Search API 使用。

默认流程：

1. 抓取 GitHub Trending `daily / weekly / monthly` 页面。
2. 解析 repo、语言、总 star、周期 star。
3. 只对初筛 repo 调用少量 `gh api`、`gh issue list`、`gh pr list`。
4. 缓存原始 HTML 和 JSON 到 `outputs/`。
5. 生成 `outputs/weekly_report.md`。

## 运行前检查

确认 GitHub CLI 已登录：

```sh
gh auth status
```

确认免费 authenticated API 额度：

```sh
gh api rate_limit --jq '{core:.resources.core, search:.resources.search, code_search:.resources.code_search, graphql:.resources.graphql}'
```

健康状态通常类似：

```json
{
  "core": {"limit": 5000, "remaining": 5000},
  "search": {"limit": 30, "remaining": 30},
  "code_search": {"limit": 10, "remaining": 10},
  "graphql": {"limit": 5000, "remaining": 5000}
}
```

## 跑第一轮筛选

从项目目录运行：

```sh
./scripts/search_repos.sh
```

更保守地只深入 10 个 repo：

```sh
MAX_REPOS=10 ./scripts/search_repos.sh
```

如果已经抓过 Trending HTML，只想复用缓存：

```sh
./scripts/search_repos.sh --skip-fetch --max-repos 10
```

## 输出文件

```text
outputs/raw/                         # 原始 Trending HTML
outputs/candidates/trending_repos.json
outputs/candidates/repo_context.json
outputs/candidates/repo_activity.json
outputs/candidates/scored_repos.json
outputs/rejected/rejected_repos.json
outputs/weekly_report.md
```

## 贡献流程沉淀

本项目的人工贡献流程记录在：

```text
docs/oss_contribution_workflow.md
```

重点硬门槛：

1. 选中 issue 后，写代码前必须查同 issue / 同关键词 / 同文件 / 同函数的 open PR。
2. 如果已有 PR 完全覆盖问题，不提交重复 PR。
3. 如果已有 PR 只覆盖部分问题，新 PR 必须有明确差异价值，并在 PR body 中诚实关联。
4. 进入代码前必须有本地复现路径、失败测试目标和风险判断。

已提交贡献的本地档案放在：

```text
outputs/contributions/
```

当前 IBM PR 档案：

```text
outputs/contributions/ibm-mcp-context-forge-4446/
```

## 限流策略

脚本会在 API 调用前执行：

```sh
python3 scripts/collect_repo_context.py check-rate-limit
```

默认最低预算：

```yaml
core >= 200
search >= 2
code_search >= 1
graphql >= 100
```

如果额度不足，脚本停止。遇到 `403 / 429 / secondary rate limit`，脚本也会停止，不会自动重试刷接口。

## 本地测试

```sh
python3 -m unittest discover -s tests
```

## Public Safety

This repository is designed to publish the reusable workflow, scripts, tests,
configs, and prompts only.

Generated artifacts are intentionally ignored:

```text
outputs/raw/
outputs/candidates/
outputs/rejected/
outputs/reports/
outputs/contributions/
workspace/repos/
```

Those directories may contain local paths, temporary research notes, generated
reports, or third-party repository checkouts and should not be committed.

## Codex Usage

This project was built and maintained with Codex as a development partner for:

1. GitHub repository and issue triage automation.
2. Strict contribution quality gates.
3. PR review and CI follow-up workflows.
4. Local test planning and verification.
5. Interview narrative and contribution evidence preparation.

## 当前 MVP 边界

已实现：

1. Trending-first 搜索。
2. GitHub API 限流守卫。
3. Repo 上下文收集。
4. 最近 issue / PR / commit / workflow 活动收集。
5. 硬过滤和 100 分评分。
6. Markdown 报告。

暂不做：

1. fork repo。
2. clone repo。
3. install dependencies。
4. reproduce issue。
5. 修改代码。
6. 创建正式 PR。
