# ============================================
# Prizolov Sports AI - Raindrop & Lens Noise Filter
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production CV Image Cleaning Core
# ============================================

import sys
import os
import cv2
import numpy as np
from typing import List, Optional

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
logger = logging.getLogger("PrizolovSportsAI.LensNoiseFilter")

class LensNoiseFilter:
    """Аппаратный CV-процессор для обнаружения и нейтрализации капель воды и грязи на защитном стекле камеры"""

    def __init__(self, history_size: int = 50, detection_threshold: int = 8):
        self.history_size = history_size
        self.threshold = detection_threshold
        
        # Накопительный буфер для поиска неподвижных артефактов
        self.frame_buffer: List[np.ndarray] = []
        self.static_mask: Optional[np.ndarray] = None

    def update_and_clean_lens_artifacts(self, frame: np.ndarray) -> np.ndarray:
        """
        Анализирует временную стабильность кадра, выжигает статический погодный шум 
        и возвращает очищенное изображение для YOLOv10.
        """
        if frame is None or frame.size == 0:
            return frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Уменьшаем разрешение для ускорения расчета маски шума (экономия CPU)
        small_gray = cv2.resize(gray, (320, 240))
        self.frame_buffer.append(small_gray)

        if len(self.frame_buffer) > self.history_size:
            self.frame_buffer.pop(0)

        # Статическая маска вычисляется только при полном заполнении временного буфера
        if len(self.frame_buffer) == self.history_size:
            # Вычисляем стандартное отклонение пикселей во времени
            std_dev = np.std(np.stack(self.frame_buffer, axis=0), axis=0)
            
            # Зоны, где пиксели практически не менялись (std < threshold), но имеют контуры, 
            # признаются статическим артефактом на стекле (капля)
            _, binary_mask = cv2.threshold(std_dev.astype(np.uint8), self.threshold, 255, cv2.THRESH_BINARY_INV)
            
            # Масштабируем бинарную маску капель обратно под исходный размер кадра трансляции
            self.static_mask = cv2.resize(binary_mask, (frame.shape[1], frame.shape[0]), interpolation=cv2.INTER_NEAREST)

        # Если маска капель сформирована, выполняем локальное восстановление текстур (Inpainting)
        if self.static_mask is not None and np.count_nonzero(self.static_mask) > 0:
            # Проверяем, чтобы площадь капель не превышала 15% кадра (иначе камера полностью залита)
            if (np.count_nonzero(self.static_mask) / self.static_mask.size) < 0.15:
                # Нативное быстрое восстановление пикселей на основе метода Навье-Стокса (cv2.INPAINT_NS)
                cleaned_frame = cv2.inpaint(frame, self.static_mask, inpaintRadius=5, flags=cv2.INPAINT_NS)
                return cleaned_frame
                
        return frame
