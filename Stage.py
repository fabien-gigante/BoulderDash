import arcade

class Stage:
    def __init__(self, game, file: str):
        self.game = game
        self.tiles = []
        self.start_x = 10 ; self.start_y = 10