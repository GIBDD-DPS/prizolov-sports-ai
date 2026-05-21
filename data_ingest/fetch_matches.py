def fetch_matches():
    return [
        {
            "teamA": [
                {"name": "A1", "attack": 70, "defense": 50},
                {"name": "A2", "attack": 65, "defense": 55}
            ],
            "teamB": [
                {"name": "B1", "attack": 60, "defense": 60},
                {"name": "B2", "attack": 58, "defense": 62}
            ]
        }
    ]

if __name__ == "__main__":
    matches = fetch_matches()
    print(matches)