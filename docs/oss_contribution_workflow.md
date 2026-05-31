# OSS Agent Contribution Workflow

This is the operating workflow for finding, validating, and preparing high-quality AI Agent / LLM engineering open-source contributions.

The goal is not to create many PRs. The goal is to find issues where a small, well-tested contribution has a realistic chance of being reviewed, accepted, and explained clearly in an interview.

## Ethical Boundary

This project must not become a PR farming tool.

The workflow exists to spend local automation, careful review time, and AI tokens before bothering maintainers. It should help contributors reject weak opportunities earlier, not mass-produce low-value pull requests.

Non-goals:

1. Generating typo-only, spelling-only, naming-only, formatting-only, or cosmetic PRs.
2. Creating PRs just to appear active.
3. Producing automated patches without reading the repository context.
4. Treating maintainer review time as free.
5. Chasing labels, badges, or contribution counts over project value.
6. Using AI output as a substitute for understanding the bug, tests, and risk.

The correct output for a weak opportunity is rejection. Returning zero recommended projects is better than pushing contributors toward noisy or low-quality work.

High-quality use means:

1. Read the project before recommending changes.
2. Check whether someone else already solved or claimed the work.
3. Reproduce the problem locally or with a minimal harness.
4. Add tests that would have caught the failure.
5. Keep the diff reviewable.
6. Explain why the change helps the maintainer and future users.
7. Require human review before submission.

## Core Principles

1. Do not create low-quality PRs.
2. Do not submit bulk typo or cosmetic PRs.
3. Do not recommend code changes before reading the repo context.
4. Do not edit code before local reproduction and a test plan.
5. Do not push or create PRs without explicit human approval.
6. Prefer one strong contribution over many weak attempts.
7. If an opportunity is weak, reject it directly.
8. Every recommendation must include rationale, risk, and interview value.
9. Spend automation and AI tokens to protect maintainer time.
10. Do not optimize for contribution count, labels, or profile decoration.
11. Use AI to improve diligence, not to bypass understanding.

## Stage 0: Local And Rate Limit Safety

Run these before any GitHub-heavy workflow:

```sh
gh auth status
```

```sh
gh api rate_limit --jq '{core:.resources.core, search:.resources.search, code_search:.resources.code_search, graphql:.resources.graphql}'
```

Stop if remaining API budget is low. Do not repeatedly retry on `403`, `429`, or secondary rate limit errors.

## Stage 1: Repository Discovery

Use low-cost sources first:

1. GitHub Trending daily / weekly / monthly.
2. `gh search repos` with strict caps.
3. Topic and language filters.
4. Existing candidate lists from `outputs/candidates/`.

Initial signals:

1. AI Agent / MCP / tool calling / workflow / eval / RAG / memory relevance.
2. Recent commits.
3. Recent merged PRs.
4. Recent maintainer replies.
5. CI and tests.
6. Open issues with clear reproduction context.

Reject early if the project is archived, demo-only, inactive, has no tests, or has poor maintainer response patterns.

## Stage 2: Repository Triage

Collect and read:

1. `README`
2. `CONTRIBUTING`
3. `LICENSE`
4. test configuration
5. CI workflows
6. recent commits
7. recent open and merged PRs
8. recent open and closed issues

Minimum acceptance bar:

1. The project is clearly related to AI Agent / LLM engineering.
2. There is a maintained test suite.
3. CI exists.
4. The issue or contribution area is narrow enough for a small PR.
5. Maintainers recently reviewed or merged PRs.

## Stage 3: Issue Triage

Prefer issues with:

1. bug, `good first issue`, `help wanted`, `mcp-protocol`, `testing`, or similar labels.
2. concrete reproduction steps.
3. maintainer comments or clear project-owned context.
4. a likely local reproduction path.
5. a likely testable fix.
6. no assignee and no active claimant.

Reject issues that are vague, controversial, roadmap-heavy, untestable, already assigned, or mostly documentation without engineering value.

Reject issues even when they are easy if the only likely PR is a spelling fix, a superficial rename, a cosmetic UI tweak, or a change that mainly creates review load without improving project behavior.

## Stage 4: Mandatory Collision Check Before Coding

This is now a hard gate because of the IBM #4446 lesson.

Before writing code for any selected issue, check for existing work that may already solve the same problem.

Run:

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

Also inspect recent PRs touching the same area:

```sh
gh pr list --repo OWNER/REPO --state open --limit 50
```

For suspiciously related PRs:

```sh
gh pr view PR_NUMBER --repo OWNER/REPO --json number,title,state,isDraft,createdAt,updatedAt,mergeStateStatus,reviewDecision,labels,url
```

```sh
gh pr diff PR_NUMBER --repo OWNER/REPO
```

Decision rules:

1. If an open PR fully solves the issue and is healthy, do not submit a duplicate PR.
2. If an open PR solves the core bug but lacks important tests, edge cases, or risk coverage, a new PR is acceptable only if it clearly adds differentiated value.
3. If submitting despite related PRs, mention them honestly in the PR body.
4. If the related PR is stale, blocked, or incomplete, explain why the new PR is still useful.
5. If unsure, prefer a short maintainer question over a speculative PR.

## Stage 5: Workspace Preparation

Only after Stages 1-4 pass:

```sh
gh auth status
```

```sh
git config user.name
```

```sh
git config user.email
```

```sh
ssh -T git@github.com
```

Then fork, clone, and create a branch.

## Stage 6: Reproduction And Root Cause

Before editing:

1. Reproduce the issue locally or with the smallest possible harness.
2. Identify the layer causing the bug.
3. Compare similar working code in the repo.
4. Write down the root-cause hypothesis.
5. Define the test that should fail before the fix.

Do not start with implementation.

## Stage 7: TDD Fix

Use red-green-refactor:

1. Add a focused failing test.
2. Run the exact test and confirm it fails for the expected reason.
3. Implement the smallest production change.
4. Run the focused test again.
5. Add boundary tests only when they protect real behavior.
6. Run adjacent tests.
7. Run a broader relevant test target.

Avoid unrelated cleanup unless it blocks the fix.

## Stage 8: PR Packaging

Before commit:

```sh
git diff
```

```sh
git diff --check
```

Stage only intended files:

```sh
git add PATH_1 PATH_2
```

Use DCO if the repo requires it:

```sh
git commit -s -m "fix(scope): concise description"
```

PR body must include:

1. Summary
2. Motivation
3. Changes
4. Test Plan
5. Risk
6. Related Issue
7. Maintainer Context
8. Interview Narrative for local notes, not necessarily in public PR

Public PR writing rules:

1. The title should be specific and easy to click, but still factual.
2. Prefer a title that names the user-visible failure mode, not just the internal patch.
3. The public PR body should be complete but not theatrical.
4. Avoid generic AI-like structure inflation. Keep paragraphs short, concrete, and tied to evidence.
5. Explain why the change is intentionally narrow.
6. Explain what is not being changed when that reduces maintainer risk.
7. Mention failed or skipped verification honestly.
8. Keep the richer interview narrative in local notes unless it helps maintainers review.
9. Do not use labels, title wording, or comments as decoration. Visibility must come from a clear failure mode, focused tests, and maintainer-relevant context.
10. A good PR title should make a maintainer immediately understand the bug class. It should not overclaim impact or sound like marketing.

Quality rule for issue fixes:

1. Fix the reported symptom.
2. Add the regression test that would have caught it.
3. Add only the boundary tests that protect the same behavior class.
4. Do not turn one issue into an architecture rewrite.
5. A stronger PR is not a larger PR. A stronger PR has clearer scope, better tests, and lower reviewer uncertainty.
6. When the reported symptom points to a broader class of adjacent failures, cover the nearest realistic boundary cases in tests, then stop.
7. Do not "fix everything nearby" unless those cases share the same root cause and can be verified without changing the PR's review shape.
8. Do not stretch a trivial change into a story. If the real contribution is trivial, reject it or keep it honest.
9. Do not hide uncertainty. If verification is partial, say so in the PR and local notes.

Human PR body rule:

1. Start with the exact behavior that failed.
2. State the root cause in one short paragraph.
3. Explain the fix as a constrained behavior change.
4. Name the regression and boundary tests.
5. Mention the main risk and why the implementation avoids it.
6. Avoid long personal motivation, excessive headings, and generated-looking prose.
7. Keep the public body useful for maintainers; keep resume/interview notes in local archives.

## Stage 9: Submit And Monitor

Default to draft PR unless ready status was explicitly approved.

After PR creation:

```sh
gh pr view PR_NUMBER --repo OWNER/REPO --json number,title,isDraft,mergeStateStatus,reviewDecision,statusCheckRollup,url
```

```sh
gh pr checks PR_NUMBER --repo OWNER/REPO
```

If labels are desirable, try only justified labels. External contributors often cannot add labels:

```sh
gh pr edit PR_NUMBER --repo OWNER/REPO --add-label bug --add-label testing
```

If GitHub returns a permissions error, do not push for labels in comments. Maintainers can apply labels if they agree with the PR.

If CLA fails:

1. Check the failed check details before guessing.
2. Compare the commit author email with the email covered by the CLA.
3. If the wrong email was used, add the CLA-covered email to GitHub or update the signed agreement contact information.
4. Amend only the commit metadata if the code is unchanged:

```sh
git -c user.name="YOUR_NAME" -c user.email="CLA_EMAIL" commit --amend --reset-author --no-edit
```

5. Update the PR branch safely:

```sh
git push --force-with-lease fork BRANCH_NAME
```

If CI shows `action_required` with no jobs:

1. Check run details with `gh run view`.
2. Check jobs with the Actions API.
3. If there are no jobs, treat it as a repository permission gate, usually requiring maintainer approval for workflow runs from an external fork.
4. Do not claim CI passed. Record that CI is waiting for maintainer approval.

## Stage 10: Interview Narrative

For every submitted PR, record:

1. What the project does.
2. Why the issue mattered.
3. How the bug was reproduced.
4. The root cause.
5. What changed.
6. What tests were added.
7. Why the PR is small enough to review.
8. What tradeoff or risk was considered.
9. What it demonstrates about AI Agent / MCP / LLM engineering judgment.

## IBM #4446 Lesson

We submitted IBM/mcp-context-forge #4446 for issue #4441.

The painful lesson: we discovered PR #4282 late. It was already open and covered the same `/mcp` redirect class. That should have been checked before coding.

The recovery was acceptable because #4446 was made differentiated:

1. It explicitly referenced #4282.
2. It added a real Starlette `Mount("/mcp")` regression test.
3. It added `raw_path` synchronization.
4. It added boundary coverage for `APP_ROOT_PATH`, canonical `/mcp/`, and RFC 9728 well-known paths.

This is still not the preferred path. The preferred path is to find related PRs before implementation.

## ChromeDevTools #1960 Lesson

We submitted ChromeDevTools/chrome-devtools-mcp #1960 for issue #1941.

What went well:

1. The issue was directly related to browser-agent tool semantics.
2. The bug was reproducible with a focused test before implementation.
3. The fix was constrained to native, single-select `<select>` options.
4. Custom ARIA option behavior was protected with a separate boundary test.
5. The public PR explained both the behavior fix and the tool-description guidance.
6. CLA failure was resolved by aligning the commit author email with the signed Google CLA identity.

New rules from this PR:

1. For browser-agent tools, distinguish snapshot visibility from actual clickable browser geometry.
2. Prefer explicit tool guidance over hidden magic, but add a narrow fallback when real agents can reasonably choose the wrong tool from the snapshot.
3. Before changing high-frequency tools such as `click`, prove the fallback does not capture custom widgets.
4. Keep code conservative and put more detail in tests and PR explanation.
5. Track CLA, title validation, and CI separately; they fail for different reasons.
6. If CI is `action_required` with no jobs, the contributor has likely done all they can until maintainers approve the workflow.

What this changes in future PRs:

1. A PR should not merely satisfy the current issue text. It should show that the contributor understands the failure class.
2. The implementation should stay small, but the tests should show the maintainer why the small fix is sufficient.
3. The PR body should read like a careful engineering note, not a generated case study.
4. Before assuming CI is blocked by code, inspect whether external-fork workflows are waiting for maintainer approval.
5. After signing a CLA, verify that the commit author email is one of the identities covered by that CLA.

## Next Opportunity Gate

Do not move from issue selection to coding until this checklist is complete:

```text
[ ] README read
[ ] CONTRIBUTING read
[ ] tests / CI identified
[ ] issue body read
[ ] issue comments read
[ ] open PRs searched by issue number
[ ] open PRs searched by title keywords
[ ] open PRs searched by touched path / function
[ ] recent merged PRs checked for same area
[ ] candidate issue is not already solved
[ ] local reproduction path identified
[ ] failing test target identified
[ ] PR scope can be explained in 2 minutes
[ ] change has real project value beyond profile decoration
[ ] maintainer review cost is justified by the fix and tests
[ ] no private data, token, local path, or generated artifact is staged
```
