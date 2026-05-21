class Athlete:
    def __init__(self, data):
        self.name = data["name"]
        self.attack = data["attack"]
        self.defense = data["defense"]

    def strength(self):
        return self.attack + self.defense