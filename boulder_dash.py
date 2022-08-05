import arcade
import random
from typing import Optional
from elements import *
from caves import *

CAVE_WIDTH = 40
CAVE_HEIGHT = 22
SCREEN_WIDTH = 32 * CAVE_WIDTH
SCREEN_HEIGHT = 32 * CAVE_HEIGHT
SCREEN_TITLE = "Boulder Dash"

class Cave:
    def __init__(self, game: "Game", level: int) -> None:
        self.game = game ; self.nb_players = 0
        self.level = level ; self.tiles = []
        for i in range(0,CAVE_HEIGHT):
            self.tiles.append([])
            for j in range(0,CAVE_WIDTH):
                tile = None
                c = CAVES[level-1][CAVE_HEIGHT-1-i][j]
                if   c == 'w': tile = Wall(game, j, i) # TODO : brick wall
                elif c == 'W': tile = Wall(game, j, i) # TODO : metal wall
                elif c == '.': tile = Soil(game, j, i)
                elif c == 'r': tile = Boulder(game, j, i)
                elif c == 'd': tile = Diamond(game, j, i)
                elif c == 'E': tile = Miner(game, j, i, self.nb_players); self.nb_players += 1
                elif c == 'X': tile = Unknown(game, j ,i) # TODO : exit
                elif c == '_': pass
                else: tile = Unknown(game, j ,i) # TODO : 'f', 'a', 'b', 'm' ...
                self.tiles[i].append(tile)
    
    def within_bounds(self, x: int ,y: int ) -> bool:
        return x >= 0 and y >= 0 and x < CAVE_WIDTH and y < CAVE_HEIGHT

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
        self.Cave = None

    def setup(self) -> None:
        self.Cave = Cave(self, 1)
        arcade.set_background_color(arcade.color.BLACK);
        self.camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

    def on_draw(self) -> None:
        self.camera.use()
        self.clear()
        self.Cave.draw()

    def on_key_press(self, key, modifiers): self.keys.append(key)
    def on_key_release(self, key, modifiers): self.keys.remove(key)
    def on_update(self, delta_time):
        self.Cave.on_update(delta_time)

def main() -> None:
    Game().setup()
    arcade.run()

if __name__ == "__main__":
    main()
