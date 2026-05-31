from __future__ import annotations

import argparse
import base64
import html
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.common import (  # noqa: E402
    CommandError,
    ROOT,
    RateLimitExceeded,
    check_rate_limit_or_exit,
    ensure_dirs,
    load_yaml,
    read_json,
    run_gh_json,
    write_json,
)


TAG_RE = re.compile(r"<[^>]+>")
ARTICLE_RE = re.compile(r"<article\b.*?</article>", re.IGNORECASE | re.DOTALL)
H2_RE = re.compile(r"<h2\b.*?</h2>", re.IGNORECASE | re.DOTALL)
REPO_HREF_RE = re.compile(r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"')
LANGUAGE_RE = re.compile(r'itemprop="programmingLanguage"[^>]*>(.*?)</span>', re.DOTALL)
DESCRIPTION_RE = re.compile(r"<p\b[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
PERIOD_STARS_RE = re.compile(r"([0-9][0-9,]*)\s+stars?\s+(today|this week|this month)", re.IGNORECASE)


def clean_text(value: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", value)).split())


def parse_int(value: Optional[str]) -> int:
    if not value:
        return 0
    digits = re.sub(r"[^0-9]", "", value)
    return int(digits) if digits else 0


def period_key(since: str) -> str:
    return {
        "daily": "dailyStars",
        "weekly": "weeklyStars",
        "monthly": "monthlyStars",
    }.get(since, f"{since}Stars")


def parse_trending_html(html_text: str, since: str, language: str) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    for block in ARTICLE_RE.findall(html_text):
        h2_match = H2_RE.search(block)
        if not h2_match:
            continue
        href_match = REPO_HREF_RE.search(h2_match.group(0))
        if not href_match:
            continue
        full_name = href_match.group(1)
        escaped = re.escape(full_name)

        desc_match = DESCRIPTION_RE.search(block)
        language_match = LANGUAGE_RE.search(block)
        stargazers_match = re.search(
            rf'href="/{escaped}/stargazers"[^>]*>(.*?)</a>',
            block,
            re.IGNORECASE | re.DOTALL,
        )
        forks_match = re.search(
            rf'href="/{escaped}/forks"[^>]*>(.*?)</a>',
            block,
            re.IGNORECASE | re.DOTALL,
        )
        period_match = PERIOD_STARS_RE.search(clean_text(block))

        repo = {
            "fullName": full_name,
            "description": clean_text(desc_match.group(1)) if desc_match else "",
            "primaryLanguage": clean_text(language_match.group(1)) if language_match else None,
            "stars": parse_int(clean_text(stargazers_match.group(1)) if stargazers_match else None),
            "forks": parse_int(clean_text(forks_match.group(1)) if forks_match else None),
            "trending": {
                "periods": [since],
                "language": language,
                period_key(since): parse_int(period_match.group(1) if period_match else None),
            },
        }
        repos.append(repo)
    return repos


def parse_trending_files(raw_dir: Path) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for path in sorted(raw_dir.glob("trending_*.html")):
        match = re.match(r"trending_([a-z]+)_(.+)\.html", path.name)
        if not match:
            continue
        since = match.group(1)
        language = match.group(2).replace("_", " ")
        repos = parse_trending_html(path.read_text(encoding="utf-8"), since=since, language=language)
        for repo in repos:
            full_name = repo["fullName"]
            existing = merged.setdefault(full_name, repo)
            if existing is repo:
                continue
            existing["stars"] = max(int(existing.get("stars") or 0), int(repo.get("stars") or 0))
            existing["forks"] = max(int(existing.get("forks") or 0), int(repo.get("forks") or 0))
            existing["description"] = existing.get("description") or repo.get("description") or ""
            existing["primaryLanguage"] = existing.get("primaryLanguage") or repo.get("primaryLanguage")
            existing_trending = existing.setdefault("trending", {})
            periods = set(existing_trending.get("periods", []))
            periods.update(repo.get("trending", {}).get("periods", []))
            existing_trending["periods"] = sorted(periods)
            for key, value in repo.get("trending", {}).items():
                if key.endswith("Stars"):
                    existing_trending[key] = max(int(existing_trending.get(key) or 0), int(value or 0))
    return sorted(
        merged.values(),
        key=lambda item: (
            int(item.get("trending", {}).get("monthlyStars") or 0),
            int(item.get("trending", {}).get("weeklyStars") or 0),
            int(item.get("stars") or 0),
        ),
        reverse=True,
    )


def decode_readme(payload: Dict[str, Any]) -> str:
    content = payload.get("content")
    if not content:
        return ""
    try:
        return base64.b64decode(content).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_test_commands(readme_text: str, files: List[str]) -> List[str]:
    text = readme_text.lower()
    candidates = [
        "pytest",
        "python -m pytest",
        "npm test",
        "pnpm test",
        "yarn test",
        "go test",
        "cargo test",
        "mvn test",
        "gradle test",
        "./gradlew test",
        "make test",
        "uv run pytest",
    ]
    commands = [command for command in candidates if command in text]
    lower_files = {path.lower() for path in files}
    if "package.json" in lower_files and not any("test" in command for command in commands):
        commands.append("npm test")
    if "pyproject.toml" in lower_files and not any("pytest" in command for command in commands):
        commands.append("pytest")
    if "pom.xml" in lower_files and not any(command == "mvn test" for command in commands):
        commands.append("mvn test")
    if ("build.gradle" in lower_files or "gradlew" in lower_files) and not any(
        "gradle" in command for command in commands
    ):
        commands.append("./gradlew test")
    if "go.mod" in lower_files and not any(command == "go test" for command in commands):
        commands.append("go test ./...")
    if "cargo.toml" in lower_files and not any(command == "cargo test" for command in commands):
        commands.append("cargo test")
    return sorted(set(commands))


def file_signals(files: List[str], readme_text: str, repo_data: Dict[str, Any]) -> Dict[str, Any]:
    lower_files = [path.lower() for path in files]
    basenames = {Path(path).name.lower() for path in lower_files}
    has_ci = any(
        path.startswith(".github/workflows/")
        or path.startswith(".circleci/")
        or path == ".travis.yml"
        or path == "azure-pipelines.yml"
        or path.endswith("jenkinsfile")
        for path in lower_files
    )
    has_tests = any(
        path.startswith(("tests/", "test/", "__tests__/", "spec/"))
        or "/tests/" in path
        or path.startswith("src/test/")
        or "/src/test/" in path
        or "/__tests__/" in path
        or path.endswith(("_test.py", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", "_test.go"))
        for path in lower_files
    )
    test_commands = extract_test_commands(readme_text, files)
    return {
        "hasReadme": bool(readme_text) or any(name.startswith("readme") for name in basenames),
        "hasContributing": "contributing.md" in basenames or ".github/contributing.md" in lower_files,
        "hasCodeOfConduct": "code_of_conduct.md" in basenames or ".github/code_of_conduct.md" in lower_files,
        "hasLicense": bool(repo_data.get("license")) or any(name.startswith("license") for name in basenames),
        "hasCi": has_ci,
        "hasTests": has_tests or bool(test_commands),
        "testCommands": test_commands,
        "manifests": sorted(
            name
            for name in [
                "package.json",
                "pyproject.toml",
                "requirements.txt",
                "setup.py",
                "pom.xml",
                "build.gradle",
                "go.mod",
                "Cargo.toml",
            ]
            if name.lower() in lower_files or name.lower() in basenames
        ),
    }


def safe_api_json(args: List[str], fallback: Any) -> Any:
    try:
        return run_gh_json(args)
    except RateLimitExceeded:
        raise
    except CommandError:
        return fallback


def enrich_candidates(input_path: Path, output_path: Path, max_repos: int, sleep_seconds: float) -> None:
    config = load_yaml(ROOT / "configs" / "strict_filters.yaml")
    check_rate_limit_or_exit(config)
    candidates = read_json(input_path, default=[])
    enriched: List[Dict[str, Any]] = []

    for index, candidate in enumerate(candidates[:max_repos], start=1):
        if index == 1 or index % 5 == 0:
            check_rate_limit_or_exit(config)
        full_name = candidate["fullName"]
        repo_data = run_gh_json(["api", f"repos/{full_name}"])
        default_branch = repo_data.get("default_branch") or "main"
        tree_payload = safe_api_json(
            ["api", f"repos/{full_name}/git/trees/{default_branch}?recursive=1"],
            fallback={"tree": []},
        )
        files = sorted(
            item.get("path", "")
            for item in tree_payload.get("tree", [])
            if item.get("type") == "blob" and item.get("path")
        )
        readme_payload = safe_api_json(["api", f"repos/{full_name}/readme"], fallback={})
        readme_text = decode_readme(readme_payload)

        enriched.append(
            {
                "fullName": full_name,
                "description": repo_data.get("description") or candidate.get("description") or "",
                "url": repo_data.get("html_url") or f"https://github.com/{full_name}",
                "stars": int(repo_data.get("stargazers_count") or candidate.get("stars") or 0),
                "forks": int(repo_data.get("forks_count") or candidate.get("forks") or 0),
                "watchers": int(repo_data.get("watchers_count") or 0),
                "primaryLanguage": repo_data.get("language") or candidate.get("primaryLanguage"),
                "license": (repo_data.get("license") or {}).get("spdx_id"),
                "createdAt": repo_data.get("created_at"),
                "updatedAt": repo_data.get("updated_at"),
                "pushedAt": repo_data.get("pushed_at"),
                "openIssuesCount": int(repo_data.get("open_issues_count") or 0),
                "defaultBranch": default_branch,
                "isArchived": bool(repo_data.get("archived")),
                "isFork": bool(repo_data.get("fork")),
                "topics": repo_data.get("topics") or [],
                "trending": candidate.get("trending", {}),
                "signals": file_signals(files, readme_text, repo_data),
                "filesSample": files[:200],
                "readmeExcerpt": readme_text[:6000],
            }
        )
        if sleep_seconds:
            time.sleep(sleep_seconds)

    write_json(output_path, enriched)
    print(f"Wrote {len(enriched)} enriched repo contexts to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect repo context with strict API budget checks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("check-rate-limit")

    parse_parser = subparsers.add_parser("parse-trending")
    parse_parser.add_argument("--raw-dir", default=str(ROOT / "outputs" / "raw"))
    parse_parser.add_argument("--out", default=str(ROOT / "outputs" / "candidates" / "trending_repos.json"))

    enrich_parser = subparsers.add_parser("enrich")
    enrich_parser.add_argument("--input", required=True)
    enrich_parser.add_argument("--output", required=True)
    enrich_parser.add_argument("--max-repos", type=int, default=25)
    enrich_parser.add_argument("--sleep-seconds", type=float, default=0.5)

    args = parser.parse_args()
    ensure_dirs()

    if args.command == "check-rate-limit":
        config = load_yaml(ROOT / "configs" / "strict_filters.yaml")
        payload = check_rate_limit_or_exit(config)
        resources = payload.get("resources", {})
        print(
            "GitHub API budget ok: "
            f"core={resources.get('core', {}).get('remaining')}, "
            f"search={resources.get('search', {}).get('remaining')}, "
            f"code_search={resources.get('code_search', {}).get('remaining')}, "
            f"graphql={resources.get('graphql', {}).get('remaining')}"
        )
    elif args.command == "parse-trending":
        repos = parse_trending_files(Path(args.raw_dir))
        write_json(Path(args.out), repos)
        print(f"Wrote {len(repos)} trending candidates to {args.out}")
    elif args.command == "enrich":
        enrich_candidates(Path(args.input), Path(args.output), args.max_repos, args.sleep_seconds)


if __name__ == "__main__":
    main()
