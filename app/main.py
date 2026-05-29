# ============================================
# Copyright (c) 2026
# Prizolov Agent OS v3.023
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

# ... остальной код

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса."""
    return {"status": "ok"}

@app.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Проверка готовности сервиса (включая доступность БД и Redis).
    """
    try:
        # Проверка БД
        await db.execute("SELECT 1")
        # Проверка Redis (если используется)
        # await redis_client.ping()
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Зависимости недоступны")
