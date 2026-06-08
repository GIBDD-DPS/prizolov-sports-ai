# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.10 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Project verification: files, versions, links, imports."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

REQUIRED_ROOT_FILES = [
    "amvera.yaml",
    "Dockerfile",
    "requirements.txt",
    "VERSION",
    "README.md",
    "CHANGELOG.md",
    ".env.example",
]

SOURCE_URLS = {
    "forebet": "https://www.forebet.com",
    "predictz": "https://www.predictz.com/predictions/",
    "betensured": "https://ru.betensured.com",
}

PRODUCTION_HEALTH = "https://prizolov-sports-dmandreyanov.amvera.io/api/v1/health"
VERSION_FILE = ROOT / "VERSION"
COPYRIGHT_RE = re.compile(r"PRIZOLOV SPORTS AI v14\.\d+ \(STORE-FRONT OPTIMIZED\)")


def check_required_files() -> list[str]:
    errors: list[str] = []
    for name in REQUIRED_ROOT_FILES:
        if not (ROOT / name).exists():
            errors.append(f"Missing required file: {name}")
    if not (BACKEND / "app" / "main.py").exists():
        errors.append("Missing backend/app/main.py")
    for venv_path in [ROOT / "venv", ROOT / ".venv", BACKEND / "venv"]:
        if venv_path.is_dir():
            errors.append(
                f"Local venv found at {venv_path.relative_to(ROOT)} — "
                "delete before Amvera upload (see docs/DEPLOY_AMVERA.md)"
            )
    return errors


def check_version_sync() -> list[str]:
    errors: list[str] = []
    if not VERSION_FILE.exists():
        return ["Missing VERSION file"]
    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    stale: list[str] = []
    scan_dirs = [BACKEND, ROOT / "frontend", ROOT / "shared", ROOT]
    for base in scan_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(p in path.parts for p in {".git", "__pycache__", "node_modules", ".next"}):
                continue
            if path.suffix not in {".py", ".ts", ".tsx", ".js", ".yaml", ".yml", ".md", ".html", ".example"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for match in COPYRIGHT_RE.finditer(text):
                if match.group(0) != f"PRIZOLOV SPORTS AI v{version} (STORE-FRONT OPTIMIZED)":
                    stale.append(str(path.relative_to(ROOT)))
                    break
    if stale:
        errors.append(f"Stale copyright version in {len(stale)} files (expected v{version})")
        errors.extend(stale[:10])
        if len(stale) > 10:
            errors.append(f"... and {len(stale) - 10} more")
    return errors


def check_links() -> list[str]:
    import httpx

    headers = {
        "User-Agent": "PRIZOLOV-Sports-AI/verify (+https://prizolov-sports-dmandreyanov.amvera.io)",
        "Accept": "text/html,application/xhtml+xml",
    }
    notes: list[str] = []
    with httpx.Client(timeout=25.0, headers=headers, follow_redirects=True) as client:
        for name, url in SOURCE_URLS.items():
            try:
                r = client.get(url)
                notes.append(f"source {name}: HTTP {r.status_code}")
                if r.status_code >= 400:
                    notes.append(f"  WARN: {url} returned {r.status_code} (may block datacenter IPs)")
            except Exception as exc:
                notes.append(f"  FAIL: {name} {url} -> {exc}")

        try:
            r = client.get(PRODUCTION_HEALTH)
            notes.append(f"production health: HTTP {r.status_code}")
            if r.status_code == 200:
                notes.append(f"  body: {r.text[:200]}")
            elif r.status_code == 503:
                notes.append("  WARN: Amvera app prizolov-sports returns 503 — check build logs and POSTGRES_* secrets")
        except Exception as exc:
            notes.append(f"  FAIL: production {exc}")
    return notes


def check_imports() -> list[str]:
    sys.path.insert(0, str(BACKEND))
    try:
        from app.main import app  # noqa: F401
        from app.core.config import settings

        if settings.amvera_app_name != "prizolov-sports":
            return [f"amvera_app_name mismatch: {settings.amvera_app_name}"]
    except Exception as exc:
        return [f"Import failed: {exc}"]
    return []


def main() -> int:
    print("PRIZOLOV SPORTS AI — verify_project")
    errors = check_required_files() + check_version_sync() + check_imports()
    print("\n## Links")
    for line in check_links():
        print(line)

    if errors:
        print("\n## Errors")
        for e in errors:
            print(f"- {e}")
        return 1

    print("\nOK: required files, imports, version headers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
