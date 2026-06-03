# Demo storefront fixtures (disabled in production).
# Teams like Zenit/Spartak and CSKA/Dynamo come from here — not from donors.

LIVE_EVENTS = [
    {
        "id": "f1",
        "sport": "football",
        "league": "РПЛ",
        "home": "Зенит",
        "away": "Спартак",
        "status": "LIVE",
        "time": "67'",
        "score": "2-1",
        "recommendations": [
            {"line": "Тотал больше 2.5", "coefficient": 1.85, "probability": 0.82, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.72, "probability": 0.78, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.65, "probability": 0.71, "confidence": "med"},
        ],
    },
    {
        "id": "f2",
        "sport": "football",
        "league": "La Liga",
        "home": "Barcelona",
        "away": "Real Madrid",
        "status": "LIVE",
        "time": "45'",
        "score": "1-1",
        "recommendations": [
            {"line": "Тотал больше 2.5", "coefficient": 1.92, "probability": 0.79, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.88, "probability": 0.74, "confidence": "high"},
            {"line": "Фора 0(-1)", "coefficient": 2.10, "probability": 0.65, "confidence": "med"},
        ],
    },
    {
        "id": "h1",
        "sport": "hockey",
        "league": "КХЛ",
        "home": "ЦСКА",
        "away": "Динамо",
        "status": "LIVE",
        "time": "2:15",
        "score": "3-2",
        "recommendations": [
            {"line": "Тотал больше 5.5", "coefficient": 1.82, "probability": 0.80, "confidence": "high"},
            {"line": "Обе забьют - ДА", "coefficient": 1.65, "probability": 0.85, "confidence": "high"},
        ],
    },
    {
        "id": "b1",
        "sport": "basketball",
        "league": "NBA",
        "home": "Los Angeles Lakers",
        "away": "Boston Celtics",
        "status": "LIVE",
        "time": "2 четверть",
        "score": "45-38",
        "recommendations": [
            {"line": "Тотал больше 210.5", "coefficient": 1.88, "probability": 0.77, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 1.95, "probability": 0.69, "confidence": "med"},
        ],
    },
    {
        "id": "t1",
        "sport": "tennis",
        "league": "ATP",
        "home": "Novak Djokovic",
        "away": "Jannik Sinner",
        "status": "LIVE",
        "time": "2 сет 4:2",
        "score": "1-1",
        "recommendations": [
            {"line": "Геймы 2 сета больше 8.5", "coefficient": 1.88, "probability": 0.76, "confidence": "high"},
            {"line": "Победа 1", "coefficient": 2.05, "probability": 0.62, "confidence": "med"},
        ],
    },
    {
        "id": "e1",
        "sport": "esports",
        "league": "CS2 Pro League",
        "home": "FaZe Clan",
        "away": "NAVI",
        "status": "LIVE",
        "time": "Map 2 - 8:7",
        "score": "1-0",
        "recommendations": [
            {"line": "Победа 1", "coefficient": 1.78, "probability": 0.70, "confidence": "med"},
            {"line": "Матч пойдет на 3-ю карту", "coefficient": 2.10, "probability": 0.65, "confidence": "high"},
        ],
    },
]

UPCOMING_EVENT_TEMPLATES = [
    ("u1", "football", "Bundesliga", "Bayern Munich", "Borussia Dortmund", 1.0, [
        {"line": "Тотал больше 2.5", "coefficient": 1.76, "probability": 0.74, "confidence": "high"},
        {"line": "Обе забьют - ДА", "coefficient": 1.70, "probability": 0.77, "confidence": "high"},
    ]),
    ("u2", "football", "Ligue 1", "PSG", "Marseille", 2.5, [
        {"line": "Победа 1", "coefficient": 1.66, "probability": 0.75, "confidence": "high"},
        {"line": "Тотал больше 2.5", "coefficient": 1.83, "probability": 0.72, "confidence": "med"},
    ]),
    ("u3", "hockey", "NHL", "Edmonton Oilers", "Colorado Avalanche", 3.0, [
        {"line": "Тотал больше 5.5", "coefficient": 1.90, "probability": 0.72, "confidence": "high"},
        {"line": "Обе забьют - ДА", "coefficient": 1.62, "probability": 0.82, "confidence": "high"},
    ]),
    ("u4", "basketball", "NBA", "Phoenix Suns", "Denver Nuggets", 4.0, [
        {"line": "Тотал больше 221.5", "coefficient": 1.98, "probability": 0.69, "confidence": "high"},
        {"line": "Фора 1 (+4.5)", "coefficient": 1.72, "probability": 0.73, "confidence": "med"},
    ]),
    ("u5", "tennis", "ATP", "Carlos Alcaraz", "Daniil Medvedev", 5.0, [
        {"line": "Тотал геймов больше 22.5", "coefficient": 1.91, "probability": 0.70, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.83, "probability": 0.67, "confidence": "med"},
    ]),
    ("u6", "volleyball", "FIVB Nations League", "Brazil", "Italy", 6.0, [
        {"line": "Тотал сетов больше 3.5", "coefficient": 1.68, "probability": 0.79, "confidence": "high"},
        {"line": "Победа 2", "coefficient": 2.08, "probability": 0.61, "confidence": "med"},
    ]),
    ("u7", "handball", "EHF Champions League", "Kiel", "Veszprem", 7.0, [
        {"line": "Тотал больше 56.5", "coefficient": 1.88, "probability": 0.72, "confidence": "high"},
        {"line": "Обе забьют более 27", "coefficient": 1.66, "probability": 0.78, "confidence": "high"},
    ]),
    ("u8", "esports", "CS2 Major", "G2", "Vitality", 8.5, [
        {"line": "Матч пойдет на 3-ю карту", "coefficient": 2.04, "probability": 0.64, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.84, "probability": 0.66, "confidence": "med"},
    ]),
    ("u9", "mma", "UFC Fight Night", "Fighter A", "Fighter B", 10.0, [
        {"line": "Победа 1", "coefficient": 1.95, "probability": 0.65, "confidence": "med"},
        {"line": "Бой продлится 3 раунда", "coefficient": 1.74, "probability": 0.71, "confidence": "high"},
    ]),
    ("u10", "baseball", "MLB", "Yankees", "Dodgers", 11.0, [
        {"line": "Тотал больше 8.5", "coefficient": 1.86, "probability": 0.70, "confidence": "high"},
        {"line": "Победа 2", "coefficient": 2.02, "probability": 0.62, "confidence": "med"},
    ]),
    ("u11", "american_football", "NFL", "Chiefs", "Bills", 12.0, [
        {"line": "Тотал больше 48.5", "coefficient": 1.92, "probability": 0.69, "confidence": "high"},
        {"line": "Фора 1 (-2.5)", "coefficient": 1.78, "probability": 0.67, "confidence": "med"},
    ]),
    ("u12", "rugby", "Super Rugby", "Crusaders", "Blues", 13.0, [
        {"line": "Тотал больше 43.5", "coefficient": 1.84, "probability": 0.72, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.88, "probability": 0.66, "confidence": "med"},
    ]),
    ("u13", "cricket", "T20 League", "Mumbai", "Chennai", 15.0, [
        {"line": "Тотал ранов больше 168.5", "coefficient": 1.80, "probability": 0.73, "confidence": "high"},
        {"line": "Победа 2", "coefficient": 2.15, "probability": 0.60, "confidence": "med"},
    ]),
    ("u14", "futsal", "UEFA Futsal Cup", "Sporting", "Benfica", 18.0, [
        {"line": "Тотал больше 5.5", "coefficient": 1.86, "probability": 0.71, "confidence": "high"},
        {"line": "Обе забьют - ДА", "coefficient": 1.58, "probability": 0.83, "confidence": "high"},
    ]),
    ("u15", "table_tennis", "WTT", "Fan Zhendong", "Ma Long", 20.0, [
        {"line": "Тотал сетов больше 4.5", "coefficient": 1.93, "probability": 0.67, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.70, "probability": 0.74, "confidence": "med"},
    ]),
    ("u16", "badminton", "BWF World Tour", "Axelsen", "Kodai Naraoka", 22.0, [
        {"line": "Тотал очков больше 74.5", "coefficient": 1.82, "probability": 0.70, "confidence": "high"},
        {"line": "Победа 1", "coefficient": 1.62, "probability": 0.78, "confidence": "high"},
    ]),
]
