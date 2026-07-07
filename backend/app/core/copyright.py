# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Copyright header utilities."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_VERSION_FILE = _ROOT / "VERSION"
_PRODUCT_VERSION = (
    _VERSION_FILE.read_text(encoding="utf-8").strip()
    if _VERSION_FILE.exists()
    else "14.38"
)

COPYRIGHT_HEADER = f"""\
# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v{_PRODUCT_VERSION} (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================
"""

PRODUCT_NAME = "PRIZOLOV SPORTS AI"
PRODUCT_VERSION = _PRODUCT_VERSION
AUTHOR = "Dm.Andreyanov"
ORGANIZATION = "Prizolov Market / Prizolov Lab"
