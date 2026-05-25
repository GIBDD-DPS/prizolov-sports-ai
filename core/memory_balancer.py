# ============================================
# Prizolov Sports AI - Memory Leak Protection
# Version: 6.02 (Adaptive GC & GPU-Aware Balancer)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Enterprise Production High-Availability
#
# CHANGELOG (5.01 → 6.02):
# - Добавлен адаптивный режим очистки (dynamic GC interval)
# - Добавлен мягкий и жесткий пороги RAM (soft/hard thresholds)
# - Добавлен мониторинг и очистка GPU-памяти (torch.cuda)
# - Добавлена защита от частых подряд "panic-clean" событий
# - Добавлен возврат статуса действия (NONE / SOFT_GC / HARD_GC)
# - Улучшен логгер: уровни, формат сообщений, метрики
# - Сохранена совместимость с Amvera Cloud и /proc/self/status
# ============================================

import sys
import os
import gc
import time
import logging
from pathlib import Path
from typing import Literal, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.MemoryBalancer")


class ProductionMemoryBalancer:
    """
    Системный менеджер очистки оперативной и (опционально) GPU-памяти
    для долгосрочных Live-трансляций и высоконагруженного инференса.
    """

    def __init__(
        self,
        max_allowed_ram_mb: float = 1540.0,
        soft_ram_ratio: float = 0.85,
        force_gc_interval_frames: int = 1200,
        min_hard_gc_cooldown_sec: int = 30
    ):
        """
        Args:
            max_allowed_ram_mb:
                Жёсткий лимит RAM для контейнера, превышение которого
                триггерит форсированную зачистку (HARD_GC).
            soft_ram_ratio:
                Доля от max_allowed_ram_mb, при превышении которой
                запускается мягкая адаптивная очистка (SOFT_GC).
            force_gc_interval_frames:
                Базовый интервал кадров для плановой профилактической
                сборки мусора (SOFT_GC).
            min_hard_gc_cooldown_sec:
                Минимальный интервал между двумя HARD_GC, чтобы
                избежать "дребезга" при колебаниях RAM.
        """
        self.max_ram = max_allowed_ram_mb
        self.soft_ram = max_allowed_ram_mb * soft_ram_ratio
        self.gc_interval_base = max(100, force_gc_interval_frames)
        self.gc_interval_current = self.gc_interval_base

        self.frame_counter = 0
        self.last_hard_gc_ts: float = 0.0
        self.min_hard_gc_cooldown_sec = min_hard_gc_cooldown_sec

    # ============================================================
    # LOW-LEVEL RAM / GPU METRICS
    # ============================================================

    def _get_current_ram_usage_mb(self) -> float:
        """Считывает текущее выделение RAM процессом из /proc/self/status."""
        try:
            with open("/proc/self/status", "r") as f:
                status_text = f.read()
            for line in status_text.split("\n"):
                if "VmRSS:" in line:
                    kb_val = int(line.split()[1])
                    return float(kb_val / 1024.0)
        except Exception:
            return 0.0
        return 0.0

    def _try_clear_gpu_cache(self) -> None:
        """Пытается освободить GPU-память, если доступен torch.cuda."""
        try:
            import torch

            if torch.cuda.is_available():
                before = torch.cuda.memory_allocated()
                torch.cuda.empty_cache()
                after = torch.cuda.memory_allocated()
                logger.info(
                    f"[Memory Balancer] GPU cache cleared: "
                    f"{before / (1024 ** 2):.2f} MB → {after / (1024 ** 2):.2f} MB"
                )
        except Exception:
            # torch может отсутствовать или быть в CPU-only режиме
            pass

    # ============================================================
    # CORE BALANCER
    # ============================================================

    def balance_resources(self) -> Literal["NONE", "SOFT_GC", "HARD_GC"]:
        """
        Вызывается внутри главного цикла инференса.

        Returns:
            "NONE"    - ничего не делали
            "SOFT_GC" - мягкая/плановая сборка мусора
            "HARD_GC" - экстренная зачистка RAM/GPU
        """
        self.frame_counter += 1
        action: Literal["NONE", "SOFT_GC", "HARD_GC"] = "NONE"

        # 1. Плановая мягкая очистка по интервалу фреймов
        if self.frame_counter % self.gc_interval_current == 0:
            gc.collect()
            logger.debug(
                f"[Memory Balancer] Плановая SOFT_GC на кадре {self.frame_counter} "
                f"(interval={self.gc_interval_current})"
            )
            action = "SOFT_GC"

        # 2. Мониторинг текущего потребления RAM
        current_usage = self._get_current_ram_usage_mb()
        if current_usage <= 0.0:
            return action

        # 2.1. Адаптивная корректировка интервала GC при приближении к soft-лимиту
        if current_usage > self.soft_ram and current_usage < self.max_ram:
            # Чем ближе к max_ram, тем чаще GC
            overload_ratio = (current_usage - self.soft_ram) / max(
                self.max_ram - self.soft_ram, 1.0
            )
            # Сжимаем интервал GC до 30% от базового при сильной нагрузке
            new_interval = int(
                self.gc_interval_base * max(0.3, 1.0 - overload_ratio)
            )
            if new_interval < self.gc_interval_current:
                logger.info(
                    f"[Memory Balancer] RAM={current_usage:.2f} MB, "
                    f"soft={self.soft_ram:.2f} MB, max={self.max_ram:.2f} MB → "
                    f"уменьшаем GC-интервал: {self.gc_interval_current} → {new_interval}"
                )
                self.gc_interval_current = max(50, new_interval)

        # 3. Экстренная жесткая зачистка при достижении критического лимита
        if current_usage > self.max_ram:
            now = time.time()
            if now - self.last_hard_gc_ts < self.min_hard_gc_cooldown_sec:
                # Уже недавно чистили — просто логируем
                logger.warning(
                    f"[Resource Danger Alert] RAM={current_usage:.2f} MB > {self.max_ram:.2f} MB, "
                    f"но HARD_GC недавно выполнялся. Пропускаем повторную зачистку."
                )
                return action

            logger.warning(
                f"[Resource Danger Alert] RAM достиг критической отметки: "
                f"{current_usage:.2f} MB / лимит {self.max_ram:.2f} MB. "
                f"Инициирована форсированная HARD_GC..."
            )

            # Полный цикл GC по поколениям
            gc.collect(0)
            gc.collect(1)
            gc.collect(2)

            # Очистка GPU-кэша (если есть)
            self._try_clear_gpu_cache()

            new_usage = self._get_current_ram_usage_mb()
            logger.info(
                f"[Resource Balancer] HARD_GC завершена. RAM: "
                f"{current_usage:.2f} MB → {new_usage:.2f} MB"
            )

            self.last_hard_gc_ts = now
            action = "HARD_GC"

            # После panic-clean можно временно ужесточить интервал GC
            self.gc_interval_current = max(50, int(self.gc_interval_base * 0.5))

        return action
