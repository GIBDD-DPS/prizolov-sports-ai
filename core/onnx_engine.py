# ============================================
# Prizolov Sports AI - ONNX Runtime Engine
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production CPU/GPU Optimization
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging
import numpy as np
from typing import List, Dict, Any, Tuple

# Нативная высокопроизводительная зависимость для Этапа 22
try:
    import onnxruntime as ort
    import cv2
except ImportError as e:
    ort = None
    cv2 = None

logger = logging.getLogger("PrizolovSportsAI.ONNXEngine")

class ONNXSportsInferenceEngine:
    """Оптимизированный движок инференса YOLOv10 через ONNX Runtime для снижения нагрузки в облаке"""

    def __init__(self, model_path: str, input_size: int = 640):
        self.model_path = model_path
        self.input_size = input_size
        self.session: Optional[ort.InferenceSession] = None
        self.input_name: Optional[str] = None
        
    def load_model(self) -> bool:
        """Инициализирует сессию ONNX Runtime с автоматическим подбором лучшего провайдера (CPU/CUDA)"""
        if ort is None or cv2 is None:
            logger.error("Ошибка: Библиотеки onnxruntime или opencv не установлены.")
            return False
            
        if not os.path.exists(self.model_path):
            logger.warning(f"Файл ONNX модели не найден по пути: {self.model_path}. Включен фолбэк-режим.")
            return False

        try:
            # Настройка оптимизаций рантайма для CPU-инференса в облаке Amvera
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4  # Ограничиваем потоки для стабильности контейнера
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # Приоритет провайдеров: ONNXExecutionProvider (GPU) -> CPU
            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.session = ort.InferenceSession(self.model_path, sess_options=opts, providers=providers)
            
            # Получаем метаданные входного тензора модели
            self.input_name = self.session.get_inputs()[0].name
            logger.info(f"[ONNX Engine] Модель успешно загружена. Провайдер: {self.session.get_providers()}")
            return True
        except Exception as e:
            logger.error(f"Критическая ошибка инициализации ONNX сессии: {e}")
            return False

    def _preprocess_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """Приводит картинку с камеры к эталонному тензору модели YOLO (1, 3, 640, 640) с нормализацией"""
        h, w, _ = frame.shape
        # Меняем размер под требования входа сети
        resized = cv2.resize(frame, (self.input_size, self.input_size))
        
        # Переводим BGR -> RGB и нормализуем пиксели в диапазон [0.0, 1.0]
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0
        
        # Переставляем оси из HWC в CHW формат: (3, 640, 640)
        chw = np.transpose(normalized, (2, 0, 1))
        
        # Добавляем размерность батча (1, 3, 640, 640)
        blob = np.expand_dims(chw, axis=0)
        
        # Коэффициенты масштабирования для возврата координат в исходные пиксели трансляции
        scale_x = w / self.input_size
        scale_y = h / self.input_size
        return blob, scale_x, scale_y

    def detect_objects(self, frame: np.ndarray, conf_threshold: float = 0.25) -> List[Dict[str, Any]]:
        """
        Выполняет скоростной векторизованный инференс кадра.
        Возвращает структурированный список детекций: [{'cls_id': 0, 'box': [x1, y1, x2, y2], 'conf': 0.89}]
        """
        if self.session is None:
            return []

        blob, scale_x, scale_y = self._preprocess_frame(frame)
        
        # Запуск вычислений C++ ядра ONNX Runtime
        outputs = self.session.run(None, {self.input_name: blob})
        
        detections = []
        # Выходной тензор YOLOv10 обычно имеет структуру [1, 300, 6] или аналогичную (зависит от экспорта)
        output_data = outputs[0]
        
        if len(output_data.shape) == 3:
            output_data = output_data[0] # Убираем размерность батча

        for pred in output_data:
            # Структура предсказания: [x1, y1, x2, y2, confidence, class_id]
            if len(pred) < 6:
                continue
                
            conf = float(pred[4])
            if conf < conf_threshold:
                continue
                
            cls_id = int(pred[5])
            
            # Возвращаем координаты к исходному размеру кадра трансляции
            x1 = float(pred[0] * scale_x)
            y1 = float(pred[1] * scale_y)
            x2 = float(pred[2] * scale_x)
            y2 = float(pred[3] * scale_y)
            
            detections.append({
                "cls_id": cls_id,
                "conf": conf,
                "box": [x1, y1, x2, y2]
            })
            
        return detections
