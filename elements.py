import arcade
from boulder_dash import *

TILE_SIZE = 64
TILE_SCALE = 0.5
MAX_SPEED = 8 # squares per second

class Element(arcade.Sprite):
    def __init__(self, game, type, x, y):
        super().__init__("Tiles/" + type + str(TILE_SIZE) + "-0.png", TILE_SCALE)
        self.game = game ; self.type = type
        self.x = x ; self.y = y;
        self.center_x = TILE_SIZE * TILE_SCALE * (x + 0.5)
        self.center_y = TILE_SIZE * TILE_SCALE * (y + 0.5)
        self.wait = 0

    def try_move(self, ix, iy):
      if self.game.stage.try_move(self, self.x + ix, self.y + iy):
          self.center_x += TILE_SIZE * TILE_SCALE * ix
          self.center_y += TILE_SIZE * TILE_SCALE * iy
          self.wait = 1 / MAX_SPEED

    def on_update(self, delta_time):
        if self.wait > 0: self.wait -= delta_time
        else: self.tick()

    def tick(self):
        pass

    def can_enter(self, entering):
        return False

    def can_move(self, into):
        return True

class Soil(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Soil", x, y)

    def can_enter(self, entering):
        return entering.type == "Miner"

class Wall(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Wall", x, y)

class Boulder(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Boulder", x, y)

    def tick(self):
        if not self.try_move(0, -1):
            if not self.try_move(-1, -1):
                self.try_move(+1, -1)

class Diamond(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Diamond", x, y)

    def tick(self):
        if not self.try_move(0, -1):

class Miner(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Miner", x, y)

    def tick(self):
        if   arcade.key.LEFT  in self.game.keys:  self.try_move(-1, 0)
        elif arcade.key.RIGHT in self.game.keys:  self.try_move(+1, 0)
        elif arcade.key.UP    in self.game.keys:  self.try_move(0, +1)
        elif arcade.key.DOWN  in self.game.keys:  self.try_move(0, -1)
