import arcade
from typing import Optional, Tuple
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
    
    def get_direction(self) -> Tuple[int,int]:
        if self.controls.up in self.game.keys: return (0,+1)
        if self.controls.left in self.game.keys: return (-1,0)
        if self.controls.down in self.game.keys: return (0,-1)
        if self.controls.right in self.game.keys: return (+1,0)
        else: return (0,0)
    
    def center_on(self, x, y) -> None:
       if self.id == 0: self.game.center_on(x, y, 0.1)

    def kill(self) -> None:
        self.life -= 1
        if any(p.life > 0 for p in self.game.players): 
            self.game.cave.set_status(Cave.FAILED)
        else: self.game.over()

class Cave:
    WIDTH = 40
    WIDTH_SMALL = 20
    HEIGHT = 22
    HEIGHT_SMALL = 12
    IN_PROGRESS = 0
    FAILED = -1
    SUCCEEDED = 1

    def __init__(self, game: "Game") -> None:
        self.game = game ; self.game.cave = self
        self.next_level(1)

    def load(self) -> None:
        types = { 'w': BrickWall, 'W': MetalWall, '.': Soil, 'r': Boulder, 'd': Diamond, 'E': Entry, 'X': Exit, \
                  'f': Firefly, 'b': Butterfly, '_': None } # TODO : m=magic wall, a=amoeba
        self.nb_diamonds = CAVES[self.level - 1][0]
        for i in range(0, Cave.HEIGHT):
            self.tiles.append([])
            for j in range(0, Cave.WIDTH):
                key = CAVES[self.level - 1][Cave.HEIGHT - i][j]
                type = types[key] if key in types else Unknown
                tile = type(self.game, j, i) if not type is None else None
                self.tiles[i].append(tile)
    
    def next_level(self, level : Optional[int] = None) -> None:
        self.level = min(CAVES.__len__(), max(1, self.level + 1 if level is None else level))
        self.width = Cave.WIDTH_SMALL if self.level % 5 ==4 else Cave.WIDTH
        self.height = Cave.HEIGHT_SMALL if self.level % 5 ==4 else Cave.HEIGHT
        self.nb_players = 0 ; self.to_collect = 0 ; self.to_kill = 0
        self.tiles = [] ; self.status = Cave.IN_PROGRESS ; self.wait = 0
        self.load()

    def restart_level(self) -> None: self.next_level(self.level)

    def is_complete(self) -> bool: 
        return self.nb_diamonds - self.game.players[0].score <= 0

    def set_status(self, status) -> None:
        self.status = status
        self.wait = 0.25 # seconds

    def within_bounds(self, x: int ,y: int) -> bool:
        return x >= 0 and y >= 0 and x < Cave.WIDTH and y < Cave.HEIGHT

    def at(self, x: int , y: int) -> Optional['Element']:
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
    TILE_SIZE = 40
    WIDTH_TILES = Cave.WIDTH_SMALL # Cave.WIDTH
    HEIGHT_TILES = Cave.HEIGHT_SMALL # Cave.HEIGHT
    WIDTH = TILE_SIZE * WIDTH_TILES
    HEIGHT = TILE_SIZE * (HEIGHT_TILES + 1)
    TITLE = 'Boulder Dash'
    FONT = 'Kenney High Square'

    def __init__(self):
        super().__init__(Game.WIDTH, Game.HEIGHT, Game.TITLE)
        self.players = [ Player(self) ]
        self.keys = []
        self.camera = None
        self.camera_gui = None
        self.cave = None
        self.center = None

    def setup(self) -> None:
        arcade.set_background_color(arcade.color.BLACK)
        self.on_resize(self.width, self.height)
        Cave(self)
    
    def on_resize(self, width: int, height: int) -> None:
        if self.camera is None or self.camera.viewport_width != width or self.camera.viewport_height != height:
            self.camera = arcade.Camera(width, height)
            self.camera_gui = arcade.Camera(width, height)
            if not self.center is None: self.center_on(*self.center)
            if width > Cave.WIDTH * Game.TILE_SIZE:
              self.camera_gui.move_to( ((Cave.WIDTH * Game.TILE_SIZE - width)/2, 0) )

    def center_on(self, x, y, speed = 1) -> None:
        self.center = (x, y)
        if self.width > Cave.WIDTH * Game.TILE_SIZE:
            cx = (Cave.WIDTH * Game.TILE_SIZE - self.width) / 2
        else:
            cx = x - self.width / 2
            if cx < 0: cx = 0
            if cx > self.cave.width * Game.TILE_SIZE - self.width : cx = self.cave.width * Game.TILE_SIZE - self.width
        if self.height > Cave.HEIGHT * Game.TILE_SIZE + Game.TILE_SIZE:
            cy = (Cave.HEIGHT * Game.TILE_SIZE + Game.TILE_SIZE -  self.height) / 2
        else:
            cy = y - self.height / 2
            if cy < 0: cy = 0
            if cy > self.cave.height * Game.TILE_SIZE - self.height + Game.TILE_SIZE : cy = self.cave.height * Game.TILE_SIZE - self.height + Game.TILE_SIZE
        self.camera.move_to((cx, cy) , speed )

    def print(self, x: int, w:int, value) -> None:
        (color, align, w) = (arcade.color.WHITE, 'left', w) if w >= 0 else (arcade.color.YELLOW, 'right', -w)
        h = Cave.HEIGHT * Game.TILE_SIZE + 4* Game.TILE_SIZE if self.height > Game.HEIGHT else Game.HEIGHT
        arcade.draw_text(str(value), x*Game.TILE_SIZE, h - 7/8 * Game.TILE_SIZE, color, Game.TILE_SIZE, w * Game.TILE_SIZE, align, Game.FONT)

    def on_draw(self) -> None:
        self.camera.use()
        self.clear()
        self.cave.draw()

        self.camera_gui.use()
        self.print(0, 5, 'LEVEL') ; self.print(0, -5, self.cave.level)
        self.print(10, 5, 'LIFE') ; self.print(10, -5, self.players[0].life)
        self.print(30, 5, 'SCORE') ; self.print(30, -10, self.players[0].score)

    def on_key_press(self, key, modifiers): 
        self.keys.append(key)
        if key == arcade.key.NUM_ADD : self.cave.next_level()
        elif key == arcade.key.NUM_SUBTRACT : self.cave.next_level(self.cave.level - 1)
        elif key == arcade.key.NUM_MULTIPLY : self.players = [ Player(self) ] ; self.cave.restart_level()
        elif key == arcade.key.ENTER and modifiers & arcade.key.MOD_ALT : self.set_fullscreen(not self.fullscreen)

    def on_key_release(self, key, modifiers):
       if key in self.keys: self.keys.remove(key)

    def on_update(self, delta_time):
        self.cave.on_update(delta_time)

    def over(self) -> None:
        pass # TODO

def main() -> None:
    Game().setup()
    arcade.run()

if __name__ == '__main__':
    main()
