from models.athlete import Athlete

class Team:
    def __init__(self, players, name="Team"):
        self.name = name
        self.players = [Athlete(p) for p in players]

    def strength(self):
        total = sum(p.strength() for p in self.players)
        return total / len(self.players)