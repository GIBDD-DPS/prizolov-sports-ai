# ============================================
# Prizolov Sports AI - ONNX Runtime Engine
# Version: 5.02 (Minor Refactor & Cleanup)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: Production CPU/GPU Optimization
#
# CHANGELOG (5.01 → 5.02):
# - Удалены неиспользуемые импорты (os, Tuple)
# - Добавлены недостающие типы Optional
# - Уточнены docstring-и
# - Упрощена проверка наличия onnxruntime/opencv
# - Лёгкая чистка структуры кода без изменения логики
# ============================================

import sys
from pathlib import Path
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Нативная высокопроизводительная зависимость для Этапа 22
try:
    import onnxruntime as ort
    import cv2
except ImportError:
    ort = None
    cv2 = None

logger = logging.getLogger("PrizolovSportsAI.ONNXEngine")


class ONNXSportsInferenceEngine:
    """Оптимизированный движок инференса YOLOv10 через ONNX Runtime для снижения нагрузки в облаке."""

    def __init__(self, model_path: str, input_size: int = 640) -> None:
        self.model_path = model_path
        self.input_size = input_size
        self.session: Optional[ort.InferenceSession] = None
        self.input_name: Optional[str] = None

    def load_model(self) -> bool:
        """
        Инициализирует сессию ONNX Runtime с автоматическим подбором лучшего провайдера (CPU/CUDA).
        """
        if ort is None or cv2 is None:
            logger.error("Ошибка: Библиотеки onnxruntime или opencv не установлены.")
            return False

        if not self.model_path or not Path(self.model_path).exists():
            logger.warning(f"Файл ONNX модели не найден по пути: {self.model_path}. Включен фолбэк-режим.")
            return False

        try:
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = 4
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.session = ort.InferenceSession(self.model_path, sess_options=opts, providers=providers)

            self.input_name = self.session.get_inputs()[0].name
            logger.info(f"[ONNX Engine] Модель успешно загружена. Провайдер: {self.session.get_providers()}")
            return True

        except Exception as e:
            logger.error(f"Критическая ошибка инициализации ONNX сессии: {e}")
            return False

    def _preprocess_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        Приводит картинку к тензору YOLO (1, 3, input_size, input_size) с нормализацией.
        """
        h, w, _ = frame.shape

        resized = cv2.resize(frame, (self.input_size, self.input_size))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = rgb.astype(np.float32) / 255.0

        chw = np.transpose(normalized, (2, 0, 1))
        blob = np.expand_dims(chw, axis=0)

        scale_x = w / self.input_size
        scale_y = h / self.input_size

        return blob, scale_x, scale_y

    def detect_objects(self, frame: np.ndarray, conf_threshold: float = 0.25) -> List[Dict[str, Any]]:
        """
        Выполняет инференс кадра и возвращает список детекций:
        [{'cls_id': int, 'box': [x1, y1, x2, y2], 'conf': float}]
        """
        if self.session is None:
            return []

        blob, scale_x, scale_y = self._preprocess_frame(frame)

        outputs = self.session.run(None, {self.input_name: blob})
        output_data = outputs[0]

        if len(output_data.shape) == 3:
            output_data = output_data[0]

        detections: List[Dict[str, Any]] = []

        for pred in output_data:
            if len(pred) < 6:
                continue

            conf = float(pred[4])
            if conf < conf_threshold:
                continue

            cls_id = int(pred[5])

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
