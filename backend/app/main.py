# ============================================
# Copyright (c) 2026
# PRIZOLOV SPORTS AI v14.18 (STORE-FRONT OPTIMIZED)
# Author: Dm.Andreyanov
# Organization: Prizolov Market / Prizolov Lab
# ============================================

import json
from fastapi.responses import HTMLResponse
from fastapi import Request
from sqlalchemy import text
from app.db.session import SessionLocal # Импорт сессии из ваших настроек

@app.get("/api/v1/storefront-widget", response_class=HTMLResponse)
async def get_storefront_widget(request: Request):
    predictions = []
    try:
        # Выполняем прямой чистый SQL-запрос к таблице predictions, созданной на Шаге 6
        with SessionLocal() as session:
            result = session.execute(
                text("SELECT home_team, away_team, prediction, probability, factors FROM predictions LIMIT 50")
            )
            # Превращаем результат в массив словарей
            for row in result:
                predictions.append({
                    "home_team": row[0],
                    "away_team": row[1],
                    "prediction": row[2],
                    "probability": row[3],
                    "factors": row[4]
                })
    except Exception as e:
        # Если таблица называется чуть иначе, запишем ошибку, но контейнер не упадет
        error_msg = str(e)
    
    # Формируем HTML-код карточек матчей
    cards_html = ""
    if not predictions:
        cards_html = f'<p style="color:#aaa; text-align:center; width:100%; font-style:italic;">Ближайших событий не найдено. (Статус: {error_msg if "error_msg" in locals() else "OK"})</p>'
    else:
        for item in predictions:
            home = item.get("home_team") or "Команда А"
            away = item.get("away_team") or "Команда Б"
            prediction_type = item.get("prediction") or "1X2"
            probability = f"{item.get('probability')}%" if item.get("probability") else "—"
            
            cards_html += f"""
            <div style="background:#1a1a1a; border:1px solid #2a2a2a; border-radius:12px; padding:20px; border-top:3px solid #00ff66; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 4px 10px rgba(0,0,0,0.2);">
                <div style="font-size:18px; font-weight:600; color:#fff; margin-bottom:14px; line-height:1.4;">{home} <span style="color:#555; font-weight:400;">vs</span> {away}</div>
                <div style="background:#222; padding:10px 15px; border-radius:8px; display:flex; justify-content:space-between; align-items:center; border:1px solid #2b2b2b;">
                    <span style="color:#aaa; font-size:14px;">Исход: <strong style="color:#00ff66;">{prediction_type}</strong></span>
                    <span style="background:#00ff66; color:#000; padding:3px 9px; border-radius:6px; font-size:13px; font-weight:bold;">{probability}</span>
                </div>
            </div>
            """

    # Полная верстка независимого виджета
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PRIZOLOV Live Storefront</title>
        <style>
            body {{ background: #141414; color: #ffffff; font-family: sans-serif; padding: 20px; margin: 0; }}
            .wrapper {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222; padding-bottom: 15px; margin-bottom: 20px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="header">
                <h2 style="color:#00ff66; margin:0; font-size:22px; font-weight:700; text-transform:uppercase; letter-spacing:1px;">PRIZOLOV SPORTS AI</h2>
                <span style="background:#222; color:#00ff66; padding:4px 12px; border-radius:20px; font-size:11px; font-weight:bold; border:1px solid #00ff66;">LIVE WIDGET</span>
            </div>
            <div class="grid">
                {cards_html}
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)
