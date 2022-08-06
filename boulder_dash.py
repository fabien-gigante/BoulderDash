import arcade
from typing import Optional
from elements import *
from caves import *
from collections import namedtuple

class Player:
    Controls = namedtuple('Controls', 'up left down right')

    def __init__(self, game: 'Game', id: int = 0) -> None:
        self.game = game ; self.id = id; self.score = 0 ; self.life = 3
        self.controls = \
            Player.Controls(arcade.key.UP, arcade.key.LEFT, arcade.key.DOWN, arcade.key.RIGHT) if id == 0 else \
            Player.Controls(arcade.key.Z, arcade.key.Q, arcade.key.S, arcade.key.D) if id == 1 else \
            Player.Controls(arcade.key.I, arcade.key.J, arcade.key.K, arcade.key.L)
    
    def pressed_up(self) -> bool: return self.controls.up in self.game.keys
    def pressed_left(self) -> bool: return self.controls.left in self.game.keys
    def pressed_down(self) -> bool: return self.controls.down in self.game.keys
    def pressed_right(self) -> bool: return self.controls.right in self.game.keys

    def kill(self) -> None:
        self.life -= 1
        if any(p.life > 0 for p in self.game.players): 
            self.game.cave.set_status(Cave.FAILED)
        else: self.game.over()

class Cave:
    WIDTH = 40
    HEIGHT = 22
    IN_PROGRESS = 0
    FAILED = -1
    SUCCEEDED = 1

    def __init__(self, game: "Game") -> None:
        self.game = game ; self.game.cave = self
        self.next_level(1)

    def load(self) -> None:
        types = { 'w': BrickWall, 'W': MetalWall, '.': Soil, 'r': Boulder, 'd': Diamond, 'E': Entry, 'X': Exit, \
                  'f': Firefly, 'b': Butterfly, '_': None } # TODO : m=magic wall, a=amoeba
        for i in range(0, Cave.HEIGHT):
            self.tiles.append([])
            for j in range(0, Cave.WIDTH):
                key = CAVES[self.level - 1][Cave.HEIGHT - 1 - i][j]
                type = types[key] if key in types else Unknown
                tile = type(self.game, j, i) if not type is None else None
                self.tiles[i].append(tile)
    
    def next_level(self, level : Optional[int] = None) -> None:
        self.level = min(CAVES.__len__(), max(1, self.level + 1 if level is None else level))
        self.nb_players = 0 ; self.to_collect = 0 ; self.to_kill = 0
        self.tiles = [] ; self.status = Cave.IN_PROGRESS ; self.wait = 0
        self.load()

    def restart_level(self) -> None: self.next_level(self.level)

    def is_complete(self) -> bool: 
        return self.to_collect == 0 and self.to_kill == 0

    def set_status(self, status) -> None:
        self.status = status
        self.wait = 0.5 # seconds

    def within_bounds(self, x: int ,y: int) -> bool:
        return x >= 0 and y >= 0 and x < Cave.WIDTH and y < Cave.HEIGHT

    def at(self, x: int , y: int ) -> Optional['Element']:
        return self.tiles[y][x] if self.within_bounds(x,y) else None

    def replace(self, e1 : 'Element', e2 : Optional['Element']) -> None:
        if self.at(e1.x, e1.y) == e1: # still there ?
          self.tiles[e1.y][e1.x] = e2
          e1.on_destroy();

    def can_move(self, element: 'Element', x: int , y: int ) -> bool:
        if not self.within_bounds(x,y): return False
        tile = self.at(x,y)
        return tile is None or tile.can_be_penetrated(element)

    def try_move(self, element: 'Element', x: int , y: int ) -> bool:
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
        if self.wait > 0:
            self.wait -= delta_time
            if self.wait <= 0:
               if self.status == Cave.SUCCEEDED: self.next_level()
               elif self.status == Cave.FAILED: self.restart_level()
        for row in self.tiles:
            for tile in row:
                if not tile is None: tile.on_update(delta_time)

    def explode(self, x: int, y: int, type = None) -> None:
        if type is None: type = Explosion
        for i in range(x-1,x+2):
            for j in range(y-1,y+2):
                if self.within_bounds(i, j):
                    tile = self.tiles[j][i]
                    if tile is None or tile.can_break():
                        self.tiles[j][i] = type(self.game, i, j);
                        if not tile is None: tile.on_destroy()

class Game(arcade.Window):
    TILE_SIZE = 32
    WIDTH = TILE_SIZE * Cave.WIDTH
    HEIGHT = TILE_SIZE * (Cave.HEIGHT + 1)
    TITLE = 'Boulder Dash'

    def __init__(self):
        super().__init__(Game.WIDTH, Game.HEIGHT, Game.TITLE)
        self.players = [ Player(self) ]
        self.keys = []
        self.camera = None
        self.Cave = None

    def setup(self) -> None:
        Cave(self)
        arcade.set_background_color(arcade.color.BLACK);
        self.camera = arcade.Camera(Game.WIDTH, Game.HEIGHT)

    def on_draw(self) -> None:
        self.camera.use()
        self.clear()
        self.cave.draw()

    def on_key_press(self, key, modifiers): 
        self.keys.append(key)
        if key == arcade.key.NUM_ADD : self.cave.next_level()
        elif key == arcade.key.NUM_SUBTRACT : self.cave.next_level(self.cave.level - 1)
        elif key == arcade.key.NUM_MULTIPLY : self.players = [ Player(self) ] ; self.cave.restart_level()

    def on_key_release(self, key, modifiers): self.keys.remove(key)
    def on_update(self, delta_time):
        self.cave.on_update(delta_time)

    def over(self) -> None:
        pass # TODO

def main() -> None:
    Game().setup()
    arcade.run()

if __name__ == '__main__':
    main()
