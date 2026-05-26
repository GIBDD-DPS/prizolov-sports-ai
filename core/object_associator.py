# ============================================
# Prizolov Sports AI - Memory Leak Protection
# Version: 6.03 (Refactored & Stabilized)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Enterprise Production High-Availability
#
# CHANGELOG (6.02 → 6.03):
# - Упрощена логика адаптивного GC
# - Уточнены типы и аннотации
# - Удалены дублирующиеся проверки
# - Упорядочены блоки логики
# - Улучшена читаемость и структура
# - Логгер приведён к единому стилю
# ============================================

import sys
import os
import gc
import time
import logging
from pathlib import Path
from typing import Literal

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.MemoryBalancer")


class ProductionMemoryBalancer:
    """
    Менеджер контроля RAM/GPU для долгосрочного Live-инференса.
    Выполняет:
    - плановый GC
    - адаптивный GC при soft-limit
    - экстренный GC при hard-limit
    - очистку GPU-кэша (если доступно)
    """

    def __init__(
        self,
        max_allowed_ram_mb: float = 1540.0,
        soft_ram_ratio: float = 0.85,
        force_gc_interval_frames: int = 1200,
        min_hard_gc_cooldown_sec: int = 30
    ):
        self.max_ram = max_allowed_ram_mb
        self.soft_ram = max_allowed_ram_mb * soft_ram_ratio

        self.gc_interval_base = max(100, force_gc_interval_frames)
        self.gc_interval_current = self.gc_interval_base

        self.frame_counter = 0
        self.last_hard_gc_ts = 0.0
        self.min_hard_gc_cooldown_sec = min_hard_gc_cooldown_sec

    # ============================================================
    # METRICS
    # ============================================================

    def _get_current_ram_usage_mb(self) -> float:
        """Читает VmRSS из /proc/self/status."""
        try:
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        return float(int(line.split()[1]) / 1024.0)
        except Exception:
            return 0.0
        return 0.0

    def _try_clear_gpu_cache(self) -> None:
        """Очищает GPU-кэш, если torch.cuda доступен."""
        try:
            import torch
            if torch.cuda.is_available():
                before = torch.cuda.memory_allocated()
                torch.cuda.empty_cache()
                after = torch.cuda.memory_allocated()
                logger.info(
                    f"[Memory Balancer] GPU cache cleared: "
                    f"{before / 1e6:.1f}MB → {after / 1e6:.1f}MB"
                )
        except Exception:
            pass

    # ============================================================
    # CORE
    # ============================================================

    def balance_resources(self) -> Literal["NONE", "SOFT_GC", "HARD_GC"]:
        """
        Основной метод, вызываемый в каждом кадре инференса.

        Returns:
            "NONE"    — ничего не делали
            "SOFT_GC" — мягкая очистка
            "HARD_GC" — экстренная очистка
        """
        self.frame_counter += 1
        action: Literal["NONE", "SOFT_GC", "HARD_GC"] = "NONE"

        # -----------------------------
        # 1. Плановый GC
        # -----------------------------
        if self.frame_counter % self.gc_interval_current == 0:
            gc.collect()
            logger.debug(
                f"[Memory Balancer] Плановая SOFT_GC (frame={self.frame_counter}, interval={self.gc_interval_current})"
            )
            action = "SOFT_GC"

        # -----------------------------
        # 2. RAM мониторинг
        # -----------------------------
        current_usage = self._get_current_ram_usage_mb()
        if current_usage <= 0.0:
            return action

        # -----------------------------
        # 3. Адаптивный GC при soft-limit
        # -----------------------------
        if self.soft_ram < current_usage < self.max_ram:
            overload_ratio = (current_usage - self.soft_ram) / max(self.max_ram - self.soft_ram, 1.0)
            new_interval = int(self.gc_interval_base * max(0.3, 1.0 - overload_ratio))

            if new_interval < self.gc_interval_current:
                logger.info(
                    f"[Memory Balancer] RAM={current_usage:.1f}MB → GC interval {self.gc_interval_current} → {new_interval}"
                )
                self.gc_interval_current = max(50, new_interval)

        # -----------------------------
        # 4. HARD GC при превышении лимита
        # -----------------------------
        if current_usage > self.max_ram:
            now = time.time()

            if now - self.last_hard_gc_ts < self.min_hard_gc_cooldown_sec:
                logger.warning(
                    f"[Resource Danger Alert] RAM={current_usage:.1f}MB > {self.max_ram:.1f}MB, "
                    f"но HARD_GC недавно выполнялся — пропуск."
                )
                return action

            logger.warning(
                f"[Resource Danger Alert] RAM критичен: {current_usage:.1f}MB / {self.max_ram:.1f}MB → HARD_GC"
            )

            gc.collect(0)
            gc.collect(1)
            gc.collect(2)

            self._try_clear_gpu_cache()

            new_usage = self._get_current_ram_usage_mb()
            logger.info(
                f"[Resource Balancer] HARD_GC завершён: {current_usage:.1f}MB → {new_usage:.1f}MB"
            )

            self.last_hard_gc_ts = now
            self.gc_interval_current = max(50, int(self.gc_interval_base * 0.5))
            action = "HARD_GC"

        return action
