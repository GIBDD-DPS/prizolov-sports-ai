from data_ingest.fetch_matches import fetch_matches
from models.team import Team

def simulate_match(match):
    teamA = Team(match["teamA"], "Team A")
    teamB = Team(match["teamB"], "Team B")

    strengthA = teamA.strength()
    strengthB = teamB.strength()

    if strengthA > strengthB:
        winner = "Team A"
    elif strengthB > strengthA:
        winner = "Team B"
    else:
        winner = "Draw"

    return {
        "Team A strength": strengthA,
        "Team B strength": strengthB,
        "winner": winner
    }

if __name__ == "__main__":
    matches = fetch_matches()

    for match in matches:
        result = simulate_match(match)
        print(result)