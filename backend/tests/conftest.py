# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.40 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

"""Тесты работают на временных SQLite-файлах: переменные окружения ставятся до
первого импорта app.core.config, где настройки читаются один раз."""

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="prizolov-tests-")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP}/app.db")
os.environ.setdefault("PARSER_ENABLED", "false")
