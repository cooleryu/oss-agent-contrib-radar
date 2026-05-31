# OSS Agent Contribution Radar Operator Playbook

This playbook turns the repository into a repeatable contribution workflow.
It is intentionally strict: the system should reject weak opportunities before
they waste maintainer time.

## 1. What This Is

`oss-agent-contrib-radar` is a local workflow for finding high-quality AI Agent,
LLM engineering, automation, observability, eval, browser-agent, and multi-agent
open-source contribution opportunities.

It is not a PR farming tool. A good run can return zero recommended projects.

## 2. Five-Minute Start

Check GitHub authentication:

```sh
gh auth status
```

Check rate-limit budget:

```sh
gh api rate_limit --jq '{core:.resources.core, search:.resources.search, code_search:.resources.code_search, graphql:.resources.graphql}'
```

Run a conservative first pass:

```sh
MAX_REPOS=10 ./scripts/search_repos.sh
```

Read the generated report:

```sh
sed -n '1,220p' outputs/weekly_report.md
```

If the report recommends nothing, accept that result. Do not lower standards
just to create a PR.

## 3. The Non-Negotiable Gates

Before any repository becomes a serious candidate:

1. It must be maintained.
2. It must have tests or a clear test command.
3. It must have CI or an equivalent verification path.
4. It must be relevant to AI Agent / LLM engineering or another selected focus.
5. It must have recent maintainer activity.
6. The issue must be understandable and testable.
7. There must be no active PR already solving the same problem.
8. The likely change must be worth maintainer review time.

If any gate fails, reject the opportunity.

## 4. Collision Check

Before coding, search for duplicate or overlapping work:

```sh
gh issue view ISSUE_NUMBER --repo OWNER/REPO --comments
```

```sh
gh pr list --repo OWNER/REPO --state open --search "ISSUE_NUMBER"
```

```sh
gh pr list --repo OWNER/REPO --state all --search "KEYWORD_FROM_ISSUE"
```

```sh
gh pr list --repo OWNER/REPO --state open --search "PATH_OR_FUNCTION_NAME"
```

If an active PR already covers the fix, stop. Only continue if the new work has
clear differentiated value, such as missing regression coverage or a narrower,
safer implementation.

## 5. Reproduction Standard

Do not start from implementation. Start from evidence:

1. Reproduce the bug locally, or build the smallest mock / fixture / harness.
2. Identify the expected behavior and actual behavior.
3. Find the layer where the failure happens.
4. Write the failing test target before changing production code.
5. Record what cannot be verified.

Paid APIs, private credentials, huge downloads, or platform-specific
requirements must be called out before spending user money or time.

## 6. Fix Standard

A strong PR is not necessarily a large PR.

The target shape is:

1. A small production diff.
2. A regression test for the original failure.
3. Boundary tests for the nearest realistic adjacent failures.
4. No unrelated refactor.
5. No broad formatting churn.
6. No new dependency unless clearly justified.
7. A clear explanation of root cause, risk, and test coverage.

Do not stretch a trivial change into an inflated story. If the real change has
no project value beyond profile decoration, reject it.

## 7. PR Body Standard

A good PR body should help maintainers review faster:

1. Start with the exact behavior that failed.
2. Explain the root cause in one short paragraph.
3. Describe the constrained fix.
4. List the regression and boundary tests.
5. Name the main risk and why the implementation avoids it.
6. Link the issue and any related PRs honestly.

Keep resume and interview notes in local files. Public PR text should be useful
to maintainers, not performative.

## 8. Human Review Boundary

This workflow may generate reports, plans, diffs, draft PR bodies, and interview
notes. It should not submit final work without human review.

Before pushing or opening a PR:

```sh
git diff
```

```sh
git diff --check
```

Then stage only intended files:

```sh
git add PATH_1 PATH_2
```

If the repository requires DCO:

```sh
git commit -s -m "fix(scope): concise summary"
```

## 9. Public Safety

Never commit:

1. API keys or tokens.
2. `.env` files.
3. Local paths or private notes.
4. Generated reports containing private research.
5. Third-party checkouts.
6. `node_modules`, virtualenvs, build outputs, caches, or large artifacts.

The default `.gitignore` keeps `outputs/` and `workspace/` out of the public
repository for this reason.

## 10. Interview Narrative

For each accepted or serious PR, keep a local narrative:

1. What the project does.
2. What failed.
3. Why the failure mattered.
4. How it was reproduced.
5. What root cause was found.
6. What changed.
7. What tests proved the fix.
8. Why the maintainer could safely accept it.
9. What engineering judgment it demonstrates.
