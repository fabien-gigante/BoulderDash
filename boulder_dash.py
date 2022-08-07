import arcade
from typing import Optional, Union, Tuple, Generator
from elements import *
from caves import *
from collections import namedtuple

class Player:
    ControlKeys = namedtuple('ControlKeys', 'up left down right')

    def __init__(self, game: 'Game', id: int = 0) -> None:
        self.game = game ; self.id = id; self.score = 0 ; self.life = 3
        self.control_keys = \
            Player.ControlKeys(arcade.key.UP, arcade.key.LEFT, arcade.key.DOWN, arcade.key.RIGHT) if id == 0 else \
            Player.ControlKeys(arcade.key.Z, arcade.key.Q, arcade.key.S, arcade.key.D) if id == 1 else \
            Player.ControlKeys(arcade.key.I, arcade.key.J, arcade.key.K, arcade.key.L)
        self.controller = game.controllers[id] if id < len(game.controllers) else None

    def is_direction(self, ix, iy) -> Tuple[int,int]: 
        return self.is_key_direction(ix, iy) or self.is_ctrl_direction(ix, iy) 

    def is_key_direction(self, ix, iy) -> Tuple[int,int]:
        return (
            self.control_keys.up    in self.game.keys and (ix,iy) == (0,+1) or
            self.control_keys.left  in self.game.keys and (ix,iy) == (-1,0) or
            self.control_keys.down  in self.game.keys and (ix,iy) == (0,-1) or
            self.control_keys.right in self.game.keys and (ix,iy) == (+1,0)
        )

    def is_ctrl_direction(self, ix, iy) -> Tuple[int,int]:
        return self.controller is not None and (
            self.controller.y < -.5 and (ix,iy) == (0,+1) or
            self.controller.x < -.5 and (ix,iy) == (-1,0) or
            self.controller.y > +.5 and (ix,iy) == (0,-1) or
            self.controller.x > +.5 and (ix,iy) == (+1,0)
        )

    def center_on(self, x, y) -> None:
       if self.id == 0: self.game.center_on(x, y, 0.1)

    def kill(self) -> None:
        self.life -= 1
        if any(p.life > 0 for p in self.game.players): 
            self.game.cave.set_status(Cave.FAILED)
        else: self.game.over()

class Cave:
    WIDTH_MAX = 40
    WIDTH_MIN = 20
    HEIGHT_MAX = 22
    HEIGHT_MIN = 12
    IN_PROGRESS = 0
    FAILED = -1
    SUCCEEDED = 1

    def __init__(self, game: "Game") -> None:
        self.game = game ; self.game.cave = self
        self.next_level(1)

    def load(self) -> None:
        types = { 'w': BrickWall, 'W': MetalWall, '.': Soil, 'r': Boulder, 'd': Diamond, 'E': Entry, 'X': Exit, \
                  'f': Firefly, 'b': Butterfly, 'm': MagicWall, 'a': Amoeba, 'e': ExpandingWall, '_': None } # TODO : a=amoeba
        self.nb_players = 0 ; self.to_collect = 0 ; self.collected = 0
        self.tiles = [] ; self.status = Cave.IN_PROGRESS ; self.wait = 0
        self.height = len(CAVE_MAPS[self.level - 1])
        self.width = len(CAVE_MAPS[self.level - 1][0])
        self.to_collect = CAVE_GOALS[self.level - 1]
        for i in range(0, self.height):
            self.tiles.append([])
            for j in range(0, self.width):
                key = CAVE_MAPS[self.level - 1][self.height -1 - i][j]
                type = types[key] if key in types else Unknown
                tile = type(self.game, j, i) if not type is None else None
                self.tiles[i].append(tile)
    
    def next_level(self, level : Optional[int] = None) -> None:
        self.level = max(1, self.level % len(CAVE_MAPS) + 1 if level is None else level)
        self.load()

    def restart_level(self) -> None: self.next_level(self.level)

    def is_complete(self) -> bool:
        return self.collected >= self.to_collect
    
    def check_amoebas(self) -> None:
        count = 0 ; trapped = True
        for amoeba in self.elements(Amoeba): 
            count += 1
            if not amoeba.trapped: trapped = False
        if trapped and count > 0:
            self.replace_all(Amoeba, Diamond)
            Diamond.sound_explosion.play()
        elif count >= 200:
            self.replace_all(Amoeba, Boulder)
            Boulder.sound_fall.play()

    def set_status(self, status) -> None:
        self.status = status
        self.wait = 0.25 # seconds

    def within_bounds(self, x: int ,y: int) -> bool:
        return x >= 0 and y >= 0 and x < self.width and y < self.height

    def at(self, x: int , y: int) -> Optional['Element']:
        return self.tiles[y][x] if self.within_bounds(x,y) else None

    def replace(self, elem : 'Element', by : Union['Element', type, None]) -> None:
        if self.at(elem.x, elem.y) is elem: # still there ?
          self.tiles[elem.y][elem.x] = by(self.game, elem.x, elem.y) if isinstance(by, type) else by
          elem.on_destroy();

    def replace_all(self, cond: Optional[Union[int,type]], by: Union['Element', type, None]) -> None:
        for elem in self.elements(cond): self.replace(elem, by)

    def can_move(self, element: 'Element', x: int , y: int) -> bool:
        if not self.within_bounds(x,y): return False
        tile = self.at(x,y)
        return tile is None or tile.can_be_penetrated(element)

    def try_move(self, element: 'Element', x: int , y: int) -> bool:
        if not self.can_move(element, x, y): return False
        tile = self.at(x,y)
        self.tiles[element.y][element.x] = None
        self.tiles[y][x] = element
        element.x = x ; element.y = y
        element.on_moved(tile)
        if tile is not None and self.at(x,y) != tile: tile.on_destroy()
        return True

    def elements(self, cond: Optional[Union[int,type]] = None) -> Generator['Element', None, None]:
        for row in self.tiles:
            for tile in row:
                if tile is not None and tile.is_kind_of(cond): yield tile

    def draw(self) -> None:
        for elem in self.elements(): elem.draw()

    def on_update(self, delta_time) -> None:
        if self.wait > 0:
            self.wait -= delta_time
            if self.wait <= 0:
               if self.status == Cave.SUCCEEDED: self.next_level()
               elif self.status == Cave.FAILED: self.restart_level()
        for priority in [Element.PRIORITY_HIGH, Element.PRIORITY_MEDIUM, Element.PRIORITY_LOW]:
            for elem in self.elements(priority): elem.on_update(delta_time)
        self.check_amoebas()

    def explode(self, x: int, y: int, type : Optional[type] = None) -> None:
        if type is None: type = Explosion
        type.sound_explosion.play()
        for i in range(x-1, x+2):
            for j in range(y-1, y+2):
                if self.within_bounds(i, j):
                    tile = self.tiles[j][i]
                    if tile is None or tile.can_break():
                        self.tiles[j][i] = type(self.game, i, j);
                        if not tile is None: tile.on_destroy()

class Game(arcade.Window):
    TILE_SIZE = 40
    WIDTH_TILES = Cave.WIDTH_MIN # Cave.WIDTH_MAX
    HEIGHT_TILES = Cave.HEIGHT_MIN # Cave.HEIGHT_MAX
    WIDTH = TILE_SIZE * WIDTH_TILES
    HEIGHT = TILE_SIZE * (HEIGHT_TILES + 1)
    TITLE = 'Boulder Dash'
    FONT = 'Kenney High Square'

    def __init__(self):
        super().__init__(Game.WIDTH, Game.HEIGHT, Game.TITLE)
        self.set_icon(pyglet.image.load(f'Tiles/Miner{Element.TILE_SIZE}-0.png'))
        self.keys = []
        self.camera = None
        self.camera_gui = None
        self.cave = None
        self.center = None
        self.players = []

    def reset(self) -> None : self.players = [ Player(self) ]

    def setup(self) -> None:
        arcade.set_background_color(arcade.color.BLACK)
        self.controllers = arcade.get_game_controllers()
        self.on_resize(self.width, self.height)
        for ctrl in self.controllers: ctrl.open()
        self.reset()
        Cave(self)

    def on_resize(self, width: int, height: int) -> None:
        if self.camera is None or self.camera.viewport_width != width or self.camera.viewport_height != height:
            self.camera = arcade.Camera(width, height)
            self.camera_gui = arcade.Camera(width, height)
            if not self.center is None: self.center_on(*self.center)
            # TO FIX: formula below wrong for various values of Game.TILE_SIZE
            if width > Cave.WIDTH_MAX * Game.TILE_SIZE:
                self.camera_gui.move_to( ((Game.WIDTH - width)/2,  Game.HEIGHT - (Cave.HEIGHT_MAX+4) * Game.TILE_SIZE ))

    def center_on(self, x, y, speed = 1) -> None:
        self.center = (x, y)
        if self.width > self.cave.width * Game.TILE_SIZE:
            cx = (self.cave.width * Game.TILE_SIZE - self.width) / 2
        else:
            cx = x - self.width / 2
            if cx < 0: cx = 0
            if cx > self.cave.width * Game.TILE_SIZE - self.width : cx = self.cave.width * Game.TILE_SIZE - self.width
        if self.height > (self.cave.height + 1) * Game.TILE_SIZE:
            cy = ((self.cave.height + 1) * Game.TILE_SIZE - self.height) / 2
        else:
            cy = y - self.height / 2
            if cy < 0 : cy = 0
            if cy > (self.cave.height + 1) * Game.TILE_SIZE - self.height : cy = (self.cave.height +1) * Game.TILE_SIZE - self.height
        self.camera.move_to((cx, cy) , speed )

    def print(self, x: int, w: int, text: str) -> None:
        (color, align, w) = (arcade.color.GRULLO, 'left', w) if w >= 0 else (arcade.color.DARK_PASTEL_GREEN, 'right', -w)
        arcade.draw_text(text, x*Game.TILE_SIZE, Game.HEIGHT - 7/8 * Game.TILE_SIZE, color, Game.TILE_SIZE, w * Game.TILE_SIZE, align, Game.FONT)

    def on_draw(self) -> None:
        self.camera.use()
        self.clear()
        self.cave.draw()

        self.camera_gui.use()
        arcade.draw_lrtb_rectangle_filled(0, self.width, Game.HEIGHT, Game.HEIGHT - Game.TILE_SIZE, (0,0,0,192))
        self.print( 0, 4, 'LEVEL') ; self.print( 0, -4, f'{self.cave.level:02}')
        self.print( 5, 3, 'LIFE')  ; self.print( 5, -3, f'{self.players[0].life:01}')
        self.print( 9, 5, 'GOAL')  ; self.print( 9, -5, f'{self.cave.collected:02}/{self.cave.to_collect:02}')
        self.print(15, 5, 'SCORE') ; self.print(15, -5, f'{self.players[0].score:04}')

    def on_key_press(self, key, modifiers): 
        self.keys.append(key)
        if key == arcade.key.NUM_ADD : self.cave.next_level()
        elif key == arcade.key.NUM_SUBTRACT : self.cave.next_level(self.cave.level - 1)
        elif key == arcade.key.NUM_MULTIPLY : self.reset() ; self.cave.restart_level()
        elif key == arcade.key.NUM_DIVIDE : self.reset() ; self.cave.next_level(1)
        elif (
            (key == arcade.key.ENTER and modifiers & arcade.key.MOD_ALT) or
            (key == arcade.key.ESCAPE and self.fullscreen) or key == arcade.key.F11
        ): self.set_fullscreen(not self.fullscreen)

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
