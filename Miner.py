import arcade

TILE_SCALING = 0.5
MOVEMENT_SPEED = 5

class Miner(arcade.Sprite):
    def __init__(self, game, x, y):
        super().__init__(":resources:images/enemies/bee.png", TILE_SCALING)
        self.game = game
        self.center_x = x ; self.center_y = y

    def on_update(self, delta_time):
        if arcade.key.LEFT in self.game.keys:
          self.center_x -= MOVEMENT_SPEED
        elif arcade.key.RIGHT in self.game.keys:
          self.center_x += MOVEMENT_SPEED
