# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Sync copyright header version across project source files."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
TARGET = f"PRIZOLOV SPORTS AI v{VERSION} (STORE-FRONT OPTIMIZED)"
PATTERN = re.compile(r"PRIZOLOV SPORTS AI v14\.\d+ \(STORE-FRONT OPTIMIZED\)")
PATTERN_JS = re.compile(r"PRIZOLOV SPORTS AI v14\.\d+ \(STORE-FRONT OPTIMIZED\)")


def sync_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text, count = PATTERN.subn(TARGET, text)
    if count == 0 and "PRIZOLOV SPORTS AI v" in text:
        new_text, count = PATTERN_JS.subn(TARGET, text)
    if count == 0:
        # HTML comment / plain v14.x in frontend
        new_text2, c2 = re.subn(r"v14\.\d+", f"v{VERSION}", new_text)
        if c2:
            new_text = new_text2
            count = c2
    if count and new_text != text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> None:
    updated = 0
    for base in [ROOT / "backend", ROOT / "frontend", ROOT / "shared", ROOT]:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if any(p in path.parts for p in {".git", "__pycache__", "node_modules"}):
                continue
            if path.name in {"VERSION", "verify_project.py", "sync_copyright.py"}:
                continue
            if path.suffix not in {".py", ".ts", ".tsx", ".js", ".yaml", ".yml", ".md", ".html", ".example", ".mdc"}:
                if path.name not in {"Dockerfile", ".dockerignore"}:
                    continue
            if sync_file(path):
                updated += 1
                print(f"updated: {path.relative_to(ROOT)}")
    # package.json version
    pkg = ROOT / "frontend" / "package.json"
    if pkg.exists():
        t = pkg.read_text(encoding="utf-8")
        nt = re.sub(r'"version": "14\.\d+\.\d+"', f'"version": "{VERSION}.0"', t)
        nt = re.sub(r"PRIZOLOV SPORTS AI v14\.\d+", f"PRIZOLOV SPORTS AI v{VERSION}", nt)
        if nt != t:
            pkg.write_text(nt, encoding="utf-8")
            print("updated: frontend/package.json")
            updated += 1
    print(f"Done. {updated} files updated to v{VERSION}.")


if __name__ == "__main__":
    main()
