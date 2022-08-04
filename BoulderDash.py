from ast import Pass
import arcade
from Miner import *
from Stage import *

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Boulder Dash"
TILE_SIZE = 32

class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.keys = []
        self.sprites = None
        self.camera = None
        self.stage = None

    def setup(self):
        self.stage = Stage(self, "level1.txt")
        self.sprites = arcade.SpriteList()
        self.sprites.append( Miner(self, TILE_SIZE * self.stage.start_x, TILE_SIZE * self.stage.start_y) )
        for tile in self.stage.tiles: self.sprites.append(tile);

        arcade.set_background_color(arcade.color.AZURE);
        self.camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

    def on_draw(self):
        self.camera.use()
        self.clear()
        self.sprites.draw()

    def on_key_press(self, key, modifiers): self.keys.append(key)
    def on_key_release(self, key, modifiers): self.keys.remove(key)
    def on_update(self, delta_time):
        self.sprites.on_update(delta_time)

def main():
    Game().setup()
    arcade.run()

if __name__ == "__main__":
    main()
