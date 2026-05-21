# ============================================
# Prizolov Sports AI - 2D Radar Render Engine
# Version: 5.01 (Initial Architecture Release)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# Target: High-Performance Live UI Rendering
# ============================================

import sys
import os
from pathlib import Path

current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import List, Dict, Any

class SportsRadarRenderer:
    """Движок генерации легковесных SVG-кадров спортивного радара для фронтенда prizolov.ru"""

    def __init__(self, sport: str, view_width: int = 800, view_height: int = 500):
        self.sport = sport.lower()
        self.w = view_width
        self.h = view_height
        
        # Размеры полей для пропорционального масштабирования метров в пиксели SVG
        if self.sport == "football":
            self.field_m_x = 105.0
            self.field_m_y = 68.0
        elif self.sport == "hockey":
            self.field_m_x = 60.0
            self.field_m_y = 30.0
        elif self.sport == "basketball":
            self.field_m_x = 28.0
            self.field_m_y = 15.0
        else:
            self.field_m_x = 100.0
            self.field_m_y = 50.0

    def _scale_coords(self, m_x: float, m_y: float) -> Tuple[int, int]:
        """Переводит метрические координаты поля в пиксельные координаты SVG холста"""
        pixel_x = int((m_x / self.field_m_x) * self.w)
        pixel_y = int((m_y / self.field_m_y) * self.h)
        return pixel_x, pixel_y

    def render_svg_frame(self, ball_x: float, ball_y: float, team_a_players: List[Dict[str, Any]], team_b_players: List[Dict[str, Any]]) -> str:
        """
        Компилирует текстовую SVG-строку текущего кадра матча.
        team_a_players: [{'x': 12.5, 'y': 34.0, 'number': 10}]
        """
        # Базовая подложка спортивного поля (темно-серый хай-тек фон под стиль prizolov.ru)
        svg_lines = [
            f'<svg xmlns="http://w3.org" viewBox="0 0 {self.w} {self.h}" width="100%" height="100%">',
            f'<rect width="{self.w}" height="{self.h}" fill="#18181b" rx="8" stroke="#27272a" stroke-width="2"/>'
        ]

        # Отрисовка центральной линии поля/площадки
        mid_x = self.w // 2
        svg_lines.append(f'<line x1="{mid_x}" y1="0" x2="{mid_x}" y2="{self.h}" stroke="#3f3f46" stroke-width="2" stroke-dasharray="5,5"/>')

        # Рендеринг игроков Команды А (зеленые точки бренда Prizolov)
        for player in team_a_players:
            px, py = self._scale_coords(player.get("x", 0.0), player.get("y", 0.0))
            p_num = player.get("number", "")
            svg_lines.append(f'<circle cx="{px}" cy="{py}" r="10" fill="#04d361" stroke="#fff" stroke-width="1.5"/>')
            if p_num:
                svg_lines.append(f'<text x="{px}" y="{py+4}" font-family="sans-serif" font-size="10" font-weight="bold" fill="#121214" text-anchor="middle">{p_num}</text>')

        # Рендеринг игроков Команды Б (фиолетовые/синие точки)
        for player in team_b_players:
            px, py = self._scale_coords(player.get("x", 0.0), player.get("y", 0.0))
            p_num = player.get("number", "")
            svg_lines.append(f'<circle cx="{px}" cy="{py}" r="10" fill="#4c6ef5" stroke="#fff" stroke-width="1.5"/>')
            if p_num:
                svg_lines.append(f'<text x="{px}" y="{py+4}" font-family="sans-serif" font-size="10" font-weight="bold" fill="#fff" text-anchor="middle">{p_num}</text>')

        # Рендеринг игрового снаряда (мяч/шайба — ярко-желтая точка с эффектом пульсации)
        bx, by = self._scale_coords(ball_x, ball_y)
        svg_lines.append(f'<circle cx="{bx}" cy="{by}" r="6" fill="#ffd31d" stroke="#121214" stroke-width="1"/>')

        svg_lines.append('</svg>')
        return "".join(svg_lines)
