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
    def __init__(self, game: "Game") -> None:
        self.game = game ; 
        self.next_level(1)

    def load(self) -> None:
        for i in range(0,CAVE_HEIGHT):
            self.tiles.append([])
            for j in range(0,CAVE_WIDTH):
                tile = None
                c = CAVES[self.level - 1][CAVE_HEIGHT - 1 - i][j]
                if   c == 'w': tile = Wall(self.game, j, i)
                elif c == 'W': tile = MetalWall(self.game, j, i)
                elif c == '.': tile = Soil(self.game, j, i)
                elif c == 'r': tile = Boulder(self.game, j, i)
                elif c == 'd': tile = Diamond(self.game, j, i) ; self.nb_diamonds += 1
                elif c == 'E': tile = Miner(self.game, j, i, self.nb_players); self.nb_players += 1
                elif c == 'X': tile = Exit(self.game, j ,i)
                elif c == '_': pass
                else: tile = Unknown(self.game, j ,i) # TODO : 'f', 'a', 'b', 'm' ...
                self.tiles[i].append(tile)
    
    def next_level(self, level : Optional[int] = None) -> None:
        self.level = min(CAVES.__len__(), max(1, self.level + 1 if level is None else level))
        self.nb_players = 0 ; self.nb_diamonds = 0
        self.tiles = []
        self.load();

    def within_bounds(self, x: int ,y: int) -> bool:
        return x >= 0 and y >= 0 and x < CAVE_WIDTH and y < CAVE_HEIGHT

    def at(self, x: int , y: int ) -> Optional["Element"]:
        return self.tiles[y][x] if self.within_bounds(x,y) else None

    def replace(self, e1 : "Element", e2 : Optional["Element"]) -> None:
        if self.at(e1.x, e1.y) == e1: # still there ?
          self.tiles[e1.y][e1.x] = e2
          e1.on_destroy();

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
        if tile is not None and self.at(x,y) != tile: tile.on_destroy()
        return True

    def draw(self) -> None:
        for row in self.tiles:
            for tile in row:
                if not tile is None: tile.draw()

    def on_update(self, delta_time) -> None:
        for row in self.tiles:
            for tile in row:
                if not tile is None: tile.on_update(delta_time)

    def explode(self, x: int, y: int) -> None:
        for i in range(x-1,x+2):
            for j in range(y-1,y+2):
                if self.within_bounds(i, j):
                    tile = self.tiles[j][i]
                    if tile is None or tile.can_break():
                        self.tiles[j][i] = Explosion(self.game, i, j);

class Game(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        self.keys = []
        self.camera = None
        self.Cave = None

    def setup(self) -> None:
        self.cave = Cave(self)
        arcade.set_background_color(arcade.color.BLACK);
        self.camera = arcade.Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

    def on_draw(self) -> None:
        self.camera.use()
        self.clear()
        self.cave.draw()

    def on_key_press(self, key, modifiers): 
        self.keys.append(key)
        if key == arcade.key.NUM_ADD : self.cave.next_level()
        elif key == arcade.key.NUM_SUBTRACT : self.cave.next_level(self.cave.level - 1)
        elif key == arcade.key.NUM_MULTIPLY : self.cave.next_level(self.cave.level)

    def on_key_release(self, key, modifiers): self.keys.remove(key)
    def on_update(self, delta_time):
        self.cave.on_update(delta_time)

def main() -> None:
    Game().setup()
    arcade.run()

if __name__ == "__main__":
    main()
