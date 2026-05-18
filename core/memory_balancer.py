# ============================================
# Prizolov Sports AI - Memory Leak Protection
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Enterprise Production High-Availability
# ============================================

import sys
import os
import gc
import logging
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger("PrizolovSportsAI.MemoryBalancer")

class ProductionMemoryBalancer:
    """Системный менеджер очистки оперативной памяти для долгосрочных Live-трансляций"""

    def __init__(self, max_allowed_ram_mb: float = 1540.0, force_gc_interval_frames: int = 1200):
        """
        Args:
            max_allowed_ram_mb: Жесткий лимит RAM для контейнера Amvera, превышение которого триггерит полную зачистку
            force_gc_interval_frames: Интервал кадров (~1 минута игры) для плановой профилактической сборки мусора
        """
        self.max_ram = max_allowed_ram_mb
        self.gc_interval = force_gc_interval_frames
        self.frame_counter = 0

    def _get_current_ram_usage_mb(self) -> float:
        """Считывает текущее выделение RAM процессом из виртуальной файловой системы Linux (/proc)"""
        try:
            # Читаем статус текущего процесса в Linux контейнере
            with open('/proc/self/status', 'r') as f:
                status_text = f.read()
            # Ищем строку с размером резидентной (физической) памяти VmRSS
            for line in status_text.split('\n'):
                if 'VmRSS:' in line:
                    kb_val = int(line.split()[1])
                    return float(kb_val / 1024.0)
        except Exception:
            # Фолбэк-заглушка на случай запуска в Windows-среде разработки
            return 0.0
        return 0.0

    def balance_resources(self) -> None:
        """Вызывается внутри главного цикла инференса. Контролирует утечки памяти и фрагментацию тензоров"""
        self.frame_counter += 1
        
        # 1. Плановая мягкая очистка по интервалу фреймов
        if self.frame_counter % self.gc_interval == 0:
            gc.collect()
            logger.debug(f"[Memory Balancer] Выполнена плановая сборка мусора на кадре: {self.frame_counter}")

        # 2. Экстренная жесткая зачистка памяти при достижении критических лимитов Amvera Cloud
        current_usage = self._get_current_ram_usage_mb()
        if current_usage > self.max_ram:
            logger.warning(
                f"[Resource Danger Alert] Потребление RAM достигло критической отметки: {current_usage:.2f} MB / "
                f"Лимит: {self.max_ram} MB! Инициирована форсированная выгрузка кэша..."
            )
            
            # Принудительно очищаем внутренние кэши циклов ссылок Python
            gc.collect(0)
            gc.collect(1)
            gc.collect(2)
            
            # Сбрасываем кэш аллокатора памяти для предотвращения деградации производительности
            # (Рантауты YOLO/PyTorch часто удерживают неиспользуемые страницы памяти)
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
                
            new_usage = self._get_current_ram_usage_mb()
            logger.info(f"[Resource Balancer] Экстренная зачистка завершена. RAM снижен до: {new_usage:.2f} MB")
