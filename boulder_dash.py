import arcade
import random
from elements import *

STAGE_WIDTH = 16
STAGE_HEIGHT = 12
SCREEN_WIDTH = 32 * STAGE_WIDTH
SCREEN_HEIGHT = 32 * STAGE_HEIGHT
SCREEN_TITLE = "Boulder Dash"

class Stage:
    def __init__(self, game, level):
        self.game = game
        self.tiles = []
        for i in range(0,STAGE_HEIGHT):
            self.tiles.append([])
            for j in range(0,STAGE_WIDTH):
                tile = None
                dice = random.randint(0,3) 
                if dice == 1: tile = Soil(game, j, i)
                elif dice == 2: tile = Wall(game, j, i)
                self.tiles[i].append(tile)
        self.tiles[5][5] = Miner(game, 5, 5)

    def move(self, element, x, y):
        if x < 0 or y < 0 or x >= STAGE_WIDTH or y >= STAGE_HEIGHT:
            return False
        tile = self.tiles[y][x]
        if tile == None or tile.can_enter(element):
            self.tiles[element.y][element.x] = None
            self.tiles[y][x] = element
            element.x = x ; element.y = y
            return True
        else:
            return False

    def draw(self):
        for row in self.tiles:
            for tile in row:
                if tile != None: tile.draw()

    def on_update(self, delta_time):
        for row in self.tiles:
            for tile in row:
                if tile != None: tile.on_update(delta_time)

class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.keys = []
        self.camera = None
        self.stage = None

    def setup(self):
        self.stage = Stage(self, 1)
        arcade.set_background_color(arcade.color.AZURE);
        self.camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

    def on_draw(self):
        self.camera.use()
        self.clear()
        self.stage.draw()

    def on_key_press(self, key, modifiers): self.keys.append(key)
    def on_key_release(self, key, modifiers): self.keys.remove(key)
    def on_update(self, delta_time):
        self.stage.on_update(delta_time)

def main():
    Game().setup()
    arcade.run()

if __name__ == "__main__":
    main()
