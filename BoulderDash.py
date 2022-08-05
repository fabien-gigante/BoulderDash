import arcade
from Miner import *
from Stage import *

SCREEN_WIDTH = 32 * 16
SCREEN_HEIGHT = 32 * 12
SCREEN_TITLE = "Boulder Dash"

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
        self.sprites.append( Miner(self, self.stage.start_x, self.stage.start_y) )

        arcade.set_background_color(arcade.color.BLACK);
        self.camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

    def on_draw(self):
        self.camera.use()
        self.clear()
        self.stage.draw()
        self.sprites.draw()

    def on_key_press(self, key, modifiers): self.keys.append(key)
    def on_key_release(self, key, modifiers): self.keys.remove(key)
    def on_update(self, delta_time):
        self.sprites.on_update(delta_time)
        self.stage.on_update(delta_time)

def main():
    Game().setup()
    arcade.run()

if __name__ == "__main__":
    main()
