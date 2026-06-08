# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================
# DEPRECATED: parser is integrated into backend app (app.parser).
# Local run: cd backend && python -m app.parser.runner

import asyncio

from app.parser.runner import run_all

if __name__ == "__main__":
    asyncio.run(run_all())
