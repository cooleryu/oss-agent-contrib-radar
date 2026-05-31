from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]


class CommandError(RuntimeError):
    def __init__(self, args: List[str], returncode: int, stderr: str):
        self.args_list = args
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"command failed ({returncode}): {' '.join(args[:4])}")


class RateLimitExceeded(RuntimeError):
    pass


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value == "":
        return ""
    if value in ("true", "True"):
        return True
    if value in ("false", "False"):
        return False
    if value in ("null", "None"):
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def simple_yaml_load(text: str) -> Dict[str, Any]:
    lines: List[Tuple[int, str]] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()
        lines.append((indent, content))

    root: Dict[str, Any] = {}
    stack: List[Tuple[int, Any]] = [(-1, root)]

    for index, (indent, content) in enumerate(lines):
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("YAML list item found under non-list parent")
            parent.append(parse_scalar(content[2:]))
            continue

        if ":" not in content:
            raise ValueError(f"Unsupported YAML line: {content}")
        key, value = content.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            parent[key] = parse_scalar(value)
            continue

        next_is_list = index + 1 < len(lines) and lines[index + 1][1].startswith("- ")
        container: Any = [] if next_is_list else {}
        parent[key] = container
        stack.append((indent, container))

    return root


def load_yaml(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not path.exists():
        return default or {}
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return data or {}
    except Exception:
        return simple_yaml_load(text)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_dirs() -> None:
    for relative in [
        "outputs/raw",
        "outputs/candidates",
        "outputs/rejected",
        "outputs/reports",
        "workspace/repos",
    ]:
        (ROOT / relative).mkdir(parents=True, exist_ok=True)


def is_rate_limit_error(text: str) -> bool:
    lowered = text.lower()
    markers = [
        "api rate limit exceeded",
        "secondary rate limit",
        "rate limit",
        "http 403",
        "http 429",
        "too many requests",
    ]
    return any(marker in lowered for marker in markers)


def run_json_command(args: List[str], timeout: int = 60) -> Any:
    completed = subprocess.run(
        args,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.returncode != 0:
        combined = f"{completed.stdout}\n{completed.stderr}"
        if is_rate_limit_error(combined):
            raise RateLimitExceeded(combined.strip())
        raise CommandError(args, completed.returncode, completed.stderr.strip())
    try:
        return json.loads(completed.stdout or "null")
    except json.JSONDecodeError as exc:
        raise CommandError(args, completed.returncode, f"invalid JSON: {exc}") from exc


def run_gh_json(args: List[str], timeout: int = 60) -> Any:
    return run_json_command(["gh"] + args, timeout=timeout)


def evaluate_rate_limit(
    payload: Dict[str, Any],
    min_core: int,
    min_search: int,
    min_code_search: int,
    min_graphql: int,
) -> Tuple[bool, List[str]]:
    resources = payload.get("resources", {})
    requirements = {
        "core": min_core,
        "search": min_search,
        "code_search": min_code_search,
        "graphql": min_graphql,
    }
    reasons: List[str] = []
    for name, required in requirements.items():
        remaining = int(resources.get(name, {}).get("remaining", 0))
        if remaining < required:
            reasons.append(f"{name} remaining {remaining} < required {required}")
    return not reasons, reasons


def check_rate_limit_or_exit(config: Dict[str, Any]) -> Dict[str, Any]:
    limits = config.get("rate_limits", {})
    payload = run_gh_json(["api", "rate_limit"])
    ok, reasons = evaluate_rate_limit(
        payload,
        min_core=int(limits.get("min_core_remaining", 200)),
        min_search=int(limits.get("min_search_remaining", 2)),
        min_code_search=int(limits.get("min_code_search_remaining", 1)),
        min_graphql=int(limits.get("min_graphql_remaining", 100)),
    )
    if not ok:
        print("Stopping before GitHub API calls because rate-limit budget is low:", file=sys.stderr)
        for reason in reasons:
            print(f"- {reason}", file=sys.stderr)
        raise SystemExit(2)
    return payload


def parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def days_since(value: Optional[str], now: Optional[datetime] = None) -> Optional[float]:
    parsed = parse_iso_datetime(value)
    if not parsed:
        return None
    current = now or now_utc()
    return (current - parsed).total_seconds() / 86400


def max_iso(values: Iterable[Optional[str]]) -> Optional[str]:
    parsed_values = [value for value in values if parse_iso_datetime(value)]
    if not parsed_values:
        return None
    return max(parsed_values, key=lambda value: parse_iso_datetime(value) or datetime.min.replace(tzinfo=timezone.utc))
