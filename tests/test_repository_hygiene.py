"""Repository-level rules that no single package can check.

docs/development-rules.md A.1: no Docker, Docker Compose, Kubernetes or any container runtime.
docs/development-phases.md, Phase 1 acceptance: no container files in the repository.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache", "dist"}

CONTAINER_FILE_PATTERNS = [
    re.compile(r"^dockerfile(\..*)?$", re.IGNORECASE),
    re.compile(r"^.*\.dockerfile$", re.IGNORECASE),
    re.compile(r"^containerfile(\..*)?$", re.IGNORECASE),
    re.compile(r"^\.dockerignore$", re.IGNORECASE),
    re.compile(r"^(docker-)?compose(\..*)?\.ya?ml$", re.IGNORECASE),
    re.compile(r"^skaffold\.ya?ml$", re.IGNORECASE),
    re.compile(r"^chart\.ya?ml$", re.IGNORECASE),  # Helm
    re.compile(r"^kustomization\.ya?ml$", re.IGNORECASE),
    re.compile(r"^\.devcontainer$", re.IGNORECASE),
]

# Commands that would run or build containers, in any script, workflow or config file.
CONTAINER_COMMAND = re.compile(
    r"\b(docker|podman|kubectl|helm)\s+(run|build|compose|pull|push|apply|install)\b"
    r"|\bdocker-compose\b",
    re.IGNORECASE,
)
SCANNED_SUFFIXES = {".sh", ".ps1", ".yml", ".yaml", ".toml", ".json", ".py", ".ts", ".tsx", ".ini"}


def _files() -> list[Path]:
    out = []
    for path in ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        out.append(path)
    return out


def test_no_container_files() -> None:
    offenders = [
        str(p.relative_to(ROOT))
        for p in _files()
        if any(pattern.match(p.name) for pattern in CONTAINER_FILE_PATTERNS)
    ]
    assert offenders == []


def test_no_container_commands_in_scripts_or_config() -> None:
    this_file = Path(__file__).resolve()
    offenders = [
        str(p.relative_to(ROOT))
        for p in _files()
        if p.is_file()
        and p.suffix in SCANNED_SUFFIXES
        and p.resolve() != this_file
        and CONTAINER_COMMAND.search(p.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert offenders == []


def test_env_files_are_ignored_by_git() -> None:
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignored
    assert ".env.*" in ignored
