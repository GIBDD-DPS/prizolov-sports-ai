from data_ingest.fetch_matches import fetch_matches
from models.team import Team

def calculate_probabilities(strengthA, strengthB):
    total = strengthA + strengthB

    probA = strengthA / total
    probB = strengthB / total

    # базовая ничья
    draw = 0.15

    # уменьшаем победы из-за ничьи
    probA = probA * (1 - draw)
    probB = probB * (1 - draw)

    return probA, probB, draw


def simulate_match(match):
    teamA = Team(match["teamA"], "Team A")
    teamB = Team(match["teamB"], "Team B")

    strengthA = teamA.strength()
    strengthB = teamB.strength()

    probA, probB, draw = calculate_probabilities(strengthA, strengthB)

    return {
        "Team A strength": round(strengthA, 2),
        "Team B strength": round(strengthB, 2),
        "probabilities": {
            "Team A win": round(probA * 100, 2),
            "Team B win": round(probB * 100, 2),
            "Draw": round(draw * 100, 2)
        }
    }


if __name__ == "__main__":
    matches = fetch_matches()

    for match in matches:
        result = simulate_match(match)
        print(result)
