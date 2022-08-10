from cmath import tau
import arcade
import time
from typing import Optional, Union, Tuple, Generator
from sprites import *
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

    def center_on(self, x, y, speed = 0.1) -> None:
       if self.id == 0: self.game.center_on(x, y, speed)

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
        self.sprite_list = arcade.SpriteList()
        self.next_level(1)

    def load(self) -> None:
        types = {
           'w': BrickWall, 'W': MetalWall, 'r': Boulder, 'd': Diamond, 'E': Entry, 'X': Exit,
           'f': Firefly, 'b': Butterfly, 'a': Amoeba, 'm': MagicWall, 'e': ExpandingWall,
           'c': Crate, 'k': CrackedBoulder, 'n': Mineral, '.': Soil, ' ': None, '_': None 
        }
        self.nb_players = 0 ; self.to_collect = 0 ; self.collected = 0
        self.tiles = [] ; self.status = Cave.IN_PROGRESS ; self.wait = 0
        cave = CAVES[self.level - 1]
        self.height = len(cave['map'])
        self.width = len(cave['map'][0])
        self.to_collect = cave['goal']
        for y in range(0, self.height):
            self.tiles.append([])
            for x in range(0, self.width):
                key = cave['map'][self.height -1 - y][x]
                type = types[key] if key in types else Unknown
                tile = type(self, x, y) if not type is None else None
                self.tiles[y].append(tile)
    
    def next_level(self, level : Optional[int] = None) -> None:
        self.level = self.level + 1 if level is None else level
        if self.level < 1 : self.level += len(CAVES)
        elif self.level > len(CAVES) : self.level -= len(CAVES)
        self.load()

    def restart_level(self) -> None: self.next_level(self.level)

    def is_complete(self) -> bool:
        return self.collected >= self.to_collect
    
    def set_status(self, status) -> None:
        self.status = status
        self.wait = 0.25 # seconds

    def within_bounds(self, x: int ,y: int) -> bool:
        return x >= 0 and y >= 0 and x < self.width and y < self.height

    def at(self, x: int , y: int) -> Optional['Sprite']:
        return self.tiles[y][x] if self.within_bounds(x,y) else None
    
    def set(self, x: int , y: int, sprite: Optional['Sprite'] ) -> Optional['Sprite']:
        current = self.at(x, y)
        if self.within_bounds(x,y): self.tiles[y][x] = sprite
        return current

    def replace(self, sprite : 'Sprite', by : Union['Sprite', type, None]) -> None:
        if self.at(sprite.x, sprite.y) is sprite: # still there ?
            self.set(sprite.x, sprite.y, by(self, sprite.x, sprite.y) if isinstance(by, type) else by)
            sprite.on_destroy()

    def replace_all(self, cond: Optional[Union[int,type]], by: Union['Sprite', type, None]) -> None:
        for sprite in self.sprites(cond): self.replace(sprite, by)

    def can_move(self, sprite: 'Sprite', x: int , y: int) -> bool:
        # TODO : rather ix,iy as arguments ?
        if not self.within_bounds(x,y): return False
        tile = self.at(x,y)
        return tile is None or tile.can_be_occupied(sprite)

    def try_move(self, sprite: 'Sprite', x: int , y: int) -> bool:
        # TODO : rather ix,iy as arguments ? rather call Sprite.can_move (to allow direct overrides) ?
        if not self.can_move(sprite, x, y): return False
        if (sprite.x, sprite.y) == (x,y): return True
        self.set(sprite.x, sprite.y, None)
        tile = self.set(x,y,sprite)
        (sprite.x, sprite.y) = (x,y)
        sprite.on_moved(tile)
        if tile is not None and self.at(x,y) != tile: tile.on_destroy()
        return True

    def sprites(self, cond: Optional[Union[int,type]] = None) -> Generator['Sprite', None, None]:
        for row in self.tiles:
            for tile in row:
                if tile is not None and tile.is_kind_of(cond): yield tile

    def draw(self) -> None:
        # TODO : move the SpriteList logic to CaveView
        self.sprite_list.draw()

    def update_sprite_list(self) -> None:
        # TODO : move the SpriteList logic to CaveView
        cave_sprites = { *self.sprites() }
        for s in self.sprite_list:
           if not s in cave_sprites: self.sprite_list.remove(s)
        for s in cave_sprites:             
            if len(s.sprite_lists) == 0: self.sprite_list.append(s)

    def on_update(self, delta_time) -> None:
        if self.wait > 0:
            self.wait -= delta_time
            if self.wait <= 0:
               if self.status == Cave.SUCCEEDED: self.next_level()
               elif self.status == Cave.FAILED: self.restart_level()
        for priority in [Sprite.PRIORITY_HIGH, Sprite.PRIORITY_MEDIUM, Sprite.PRIORITY_LOW]:
            for sprite in self.sprites(priority): sprite.on_update(delta_time)
        Amoeba.on_update_cave(self)
        self.update_sprite_list()

    def explode(self, x: int, y: int, type : Optional[type] = None) -> None:
        if type is None: type = Explosion
        type.sound_explosion.play()
        for x in range(x - 1, x + 2):
            for y in range(y - 1, y + 2):
                if self.within_bounds(x, y):
                    tile = self.at(x, y)
                    if tile is None or (not isinstance(tile,type) and tile.can_break()):
                        self.set(x, y, type(self, x, y))
                        if not tile is None: tile.on_destroy()

class CaveView(arcade.View):
    def __init__(self, game: 'Game') -> None:
        super().__init__(game)
        self.game = game
        self.camera = None
        self.camera_gui = None
        self.center = None

    def on_show_view(self)  -> None:
        pass

    def on_resize(self, width: int, height: int) -> None:
        if self.camera is None or self.camera.viewport_width != width or self.camera.viewport_height != height:
            self.camera = arcade.Camera(width, height)
            self.camera_gui = arcade.Camera(width, height)
            if not self.center is None: self.center_on(*self.center)
            # TO FIX: formula below wrong for various values of Game.TILE_SIZE
            if width > Cave.WIDTH_MAX * Game.TILE_SIZE:
                self.camera_gui.move_to( ((Game.WIDTH - width)/2,  Game.HEIGHT - (Cave.HEIGHT_MAX+4) * Game.TILE_SIZE ))

    def center_on(self, x, y, speed = 1) -> None:
        self.center = (x, y) ; cave = self.game.cave; 
        width = self.game.width ; height = self.game.height
        if width > cave.width * Game.TILE_SIZE:
            cx = (cave.width * Game.TILE_SIZE - width) / 2
        else:
            cx = x - width / 2
            if cx < 0: cx = 0
            if cx > cave.width * Game.TILE_SIZE - width : cx = cave.width * Game.TILE_SIZE - width
        if height > (cave.height + 1) * Game.TILE_SIZE:
            cy = ((cave.height + 1) * Game.TILE_SIZE - height) / 2
        else:
            cy = y - height / 2
            if cy < 0 : cy = 0
            if cy > (cave.height + 1) * Game.TILE_SIZE - height : cy = (cave.height +1) * Game.TILE_SIZE - height
        self.camera.move_to((cx, cy) , speed)

    def print(self, x: int, w: int, text: str) -> None:
        (color, align, w) = (arcade.color.GRULLO, 'left', w) if w >= 0 else (arcade.color.DARK_PASTEL_GREEN, 'right', -w)
        arcade.draw_text(text, x*Game.TILE_SIZE, Game.HEIGHT - 7/8 * Game.TILE_SIZE, color, Game.TILE_SIZE, w * Game.TILE_SIZE, align, Game.FONT)

    def on_draw(self) -> None:
        #t = time.time()
        self.camera.use()
        self.clear()
        self.game.cave.draw()
        self.camera_gui.use()
        arcade.draw_lrtb_rectangle_filled(0, self.game.width, Game.HEIGHT, Game.HEIGHT - Game.TILE_SIZE, (0,0,0,192))
        self.print( 0, 4, 'LEVEL') ; self.print( 0, -4, f'{self.game.cave.level:02}')
        self.print( 5, 3, 'LIFE')  ; self.print( 5, -3, f'{self.game.players[0].life:01}')
        self.print( 9, 5, 'GOAL')  ; self.print( 9, -5, f'{self.game.cave.collected:02}/{self.game.cave.to_collect:02}')
        self.print(15, 5, 'SCORE') ; self.print(15, -5, f'{self.game.players[0].score:04}')
        #t = time.time() - t
        #print(f'on_draw : {t*1000} ms')

    def on_update(self, delta_time):
        #t = time.time()
        self.game.cave.on_update(delta_time)
        # TODO : move the SpriteList logic here
        #t = time.time() - t
        #print(f'on_update : {t*1000} ms')

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
        self.set_icon(pyglet.image.load(f'Tiles/Miner{Sprite.TILE_SIZE}-0.png'))
        self.keys = []
        self.cave = None
        self.players = []

    def reset(self) -> None : self.players = [ Player(self) ]

    def setup(self) -> None:
        arcade.set_background_color(arcade.color.BLACK)
        self.show_view(CaveView(self))
        self.current_view.on_resize(self.width, self.height) # TODO : move to CaveView.show_view
        self.controllers = arcade.get_game_controllers()
        for ctrl in self.controllers: ctrl.open()
        self.reset()
        Cave(self)

    def center_on(self, x, y, speed = 1) -> None:
        self.current_view.center_on(x, y, speed)

    def on_key_press(self, key, modifiers): 
        self.keys.append(key)
        if key == arcade.key.NUM_ADD : self.cave.next_level()
        elif key == arcade.key.NUM_SUBTRACT : self.cave.next_level(self.cave.level - 1)
        elif (key == arcade.key.NUM_MULTIPLY or key == arcade.key.F5):
           self.reset() ; self.cave.restart_level()
        elif key == arcade.key.NUM_DIVIDE : self.reset() ; self.cave.next_level(1)
        elif (
            (key == arcade.key.ENTER and modifiers & arcade.key.MOD_ALT) or
            (key == arcade.key.ESCAPE and self.fullscreen) or key == arcade.key.F11
        ): self.set_fullscreen(not self.fullscreen)

    def on_key_release(self, key, modifiers):
       if key in self.keys: self.keys.remove(key)

    def over(self) -> None:
        pass # TODO

def main() -> None:
    Game().setup()
    arcade.run()

if __name__ == '__main__':
    main()
