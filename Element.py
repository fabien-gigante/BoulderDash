import arcade

TILE_SIZE = 64
HEART_BEAT = 0.2
TILE_SCALE = 0.5

class Element(arcade.Sprite):
    def __init__(self, game, type, x, y, heartbeat = HEART_BEAT):
        super().__init__("Tiles/" + type + str(TILE_SIZE) + "-0.png", TILE_SCALE)
        self.game = game
        self.type = type
        self.x = x ; self.y = y;
        self.center_x = TILE_SIZE * TILE_SCALE * (x + 0.5)  ; self.center_y = TILE_SIZE * TILE_SCALE * (y + 0.5)
        self.heartbeat = heartbeat
        self.clock = 0

    def move(self, ix, iy):
      if self.game.stage.move(self, self.x + ix, self.y + iy):
          self.center_x += TILE_SIZE * TILE_SCALE * ix
          self.center_y += TILE_SIZE * TILE_SCALE * iy

    def on_update(self, delta_time):
        if self.heartbeat > 0 :
            self.clock += delta_time
            if self.clock >= self.heartbeat:
                self.clock -= self.heartbeat
                self.tick()

    def tick(self):
        pass

    def can_enter(self, element):
        return False

class Soil(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Soil", x, y)

    def can_enter(self, element):
        return element.type == "Miner"

class Wall(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Wall", x, y)

class Boulder(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Boulder", x, y)

    def tick(self):
        self.move(0, 0)

class Diamond(Element):
    def __init__(self, game, x, y):
        super().__init__(game, "Diamond", x, y)