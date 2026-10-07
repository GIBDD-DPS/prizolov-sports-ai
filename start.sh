#!/bin/sh
# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.43 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================
# Точка входа контейнера. Одно слово без пробелов, поэтому работает и
# когда платформа передаёт команду как имя исполняемого файла целиком
# (Amvera: run.command), и когда запускает её через shell. Приложение
# импортирует себя как пакет app и ищет статику в ./static, поэтому
# запуск из backend/.
cd "$(dirname "$0")/backend" || exit 1
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
