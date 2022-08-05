import arcade
import random
from typing import Optional
from elements import *

STAGE_WIDTH = 24
STAGE_HEIGHT = 16
SCREEN_WIDTH = 48 * STAGE_WIDTH
SCREEN_HEIGHT = 48 * STAGE_HEIGHT
SCREEN_TITLE = "Boulder Dash"

class Stage:
    def __init__(self, game: "Game", level: int) -> None:
        self.game = game
        self.level = level ; self.tiles = []
        for i in range(0,STAGE_HEIGHT):
            self.tiles.append([])
            for j in range(0,STAGE_WIDTH):
                tile = None
                dice = random.randint(0, 8) 
                if dice == 1: tile = Soil(game, j, i)
                elif dice == 2: tile = Wall(game, j, i)
                elif dice == 3: tile = Boulder(game, j, i)
                elif dice == 4: tile = Diamond(game, j, i)
                self.tiles[i].append(tile)
        self.tiles[5][5] = Miner(game, 5, 5)
    
    def within_bounds(self, x: int ,y: int ) -> bool:
        return x >= 0 and y >= 0 and x < STAGE_WIDTH and y < STAGE_HEIGHT

    def at(self, x: int , y: int ) -> Optional["Element"]:
        return self.tiles[y][x] if self.within_bounds(x,y) else None

    def replace(self, e1 : "Element", e2 : "Element") -> None:
        self.tiles[e1.y][e1.x] = e2

    def can_move(self, element: "Element", x: int , y: int ) -> bool:
        if not self.within_bounds(x,y): return False
        tile = self.at(x,y)
        return tile is None or tile.can_be_penetrated(element)

    def try_move(self, element: "Element", x: int , y: int ) -> bool:
        if not self.can_move(element, x, y): return False
        tile = self.at(x,y)
        self.tiles[element.y][element.x] = None
        self.tiles[y][x] = element
        element.x = x ; element.y = y
        element.on_moved(tile)
        return True

    def draw(self) -> None:
        for row in self.tiles:
            for tile in row:
                if not tile is None: tile.draw()

    def on_update(self, delta_time) -> None:
        for row in self.tiles:
            for tile in row:
                if not tile is None: tile.on_update(delta_time)

class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.keys = []
        self.camera = None
        self.stage = None

    def setup(self) -> None:
        self.stage = Stage(self, 1)
        arcade.set_background_color(arcade.color.BLACK);
        self.camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

    def on_draw(self) -> None:
        self.camera.use()
        self.clear()
        self.stage.draw()

    def on_key_press(self, key, modifiers): self.keys.append(key)
    def on_key_release(self, key, modifiers): self.keys.remove(key)
    def on_update(self, delta_time):
        self.stage.on_update(delta_time)

def main() -> None:
    Game().setup()
    arcade.run()

if __name__ == "__main__":
    main()
