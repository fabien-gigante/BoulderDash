import arcade
from Element import *

class Miner(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Miner", x, y)

    def tick(self):
        if   arcade.key.LEFT  in self.game.keys:  self.move(-1, 0)
        elif arcade.key.RIGHT in self.game.keys:  self.move(+1, 0)
        elif arcade.key.UP    in self.game.keys:  self.move(0, +1)
        elif arcade.key.DOWN  in self.game.keys:  self.move(0, -1)