from typing import Optional, Union, Tuple, Generator
from collections import namedtuple
import time
import math
import pyglet
import arcade
from sprites import *
from caves import CAVES

class Sound(arcade.Sound):
    ''' An audio media in the game. Preloaded. Played at moderate volume and at most once per frame (for a given sound). '''
    VOLUME = 0.5
    def __init__(self, file) -> None: 
        super().__init__(file)
        self.last_played = -math.inf
        super().play(0).delete() # force audio preloading
    def play(self, volume = VOLUME, pan: float = 0.0, loop: bool = False, speed: float = 1.0):
        now = time.time()
        if (now - self.last_played < 1/60): return
        self.last_played = now
        return super().play(volume, pan, loop, speed)

class Player:
    ''' A player in the Boulder Dash game. Handles controls, score and lifes. '''
    SCORE_FOR_LIFE = 100
    sound = Sound(":resources:sounds/laser1.wav")
    ControlKeys = namedtuple('ControlKeys', 'up left down right')

    def __init__(self, game: 'Game', num: int = 0) -> None:
        self.game = game ; self.num = num; self._score = 0 ; self.life = 3
        self.control_keys = \
            Player.ControlKeys(arcade.key.UP, arcade.key.LEFT, arcade.key.DOWN, arcade.key.RIGHT) if num == 0 else \
            Player.ControlKeys(arcade.key.Z, arcade.key.Q, arcade.key.S, arcade.key.D) if num == 1 else \
            Player.ControlKeys(arcade.key.I, arcade.key.J, arcade.key.K, arcade.key.L) if num == 2 else \
            Player.ControlKeys(arcade.key.NUM_8, arcade.key.NUM_4, arcade.key.NUM_2, arcade.key.NUM_6)
        self.controller = game.controllers[num] if num < len(game.controllers) else None

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

    @property
    def score(self) -> int: return self._score
    @score.setter
    def score(self, value : int) -> None:
        n = self._score // Player.SCORE_FOR_LIFE
        self._score = value
        if self._score // Player.SCORE_FOR_LIFE > n and self.life < 9:
            self.life += 1
            Player.sound.play()

    def kill(self) -> None:
        self.life -= 1
        if any(p.life > 0 for p in self.game.players): 
            self.game.cave.set_status(Cave.FAILED)
        else: self.game.over()

class Cave:
    ''' The grid of tiles in which the game is played. Manages map loading and sprites updates. '''

    WIDTH_MAX = 40
    WIDTH_MIN = 20
    HEIGHT_MAX = 22
    HEIGHT_MIN = 12

    IN_PROGRESS = 0
    FAILED = -1
    NOT_LOADED = -2
    SUCCEEDED = 1

    WAIT_STATUS = 0.25 # seconds

    def __init__(self, game: "Game") -> None:
        self.game = game
        self.to_collect = 0 ; self.collected = 0
        self.status = Cave.NOT_LOADED ; self.wait = 0
        self.tiles = [] ; self.back_tiles = []
        self.miner_type = None ; self.height = self.width = 0
        self.next_level(1)

    def load(self) -> None:
        types = {
           'w': BrickWall, 'W': MetalWall, 'r': Boulder, 'd': Diamond, 'E': Entry, 'X': Exit,
           'f': Firefly, 'b': Butterfly, 'a': Amoeba, 'm': MagicWall, 'e': ExpandingWall,
           'k': CrackedBoulder, 'n': Mineral,'c': WoodCrate, 'h': MetalCrate, 't': CrateTarget, 'p': Portal,
           '.': Soil, ' ': None, '_': None 
        }
        self.to_collect = 0 ; self.collected = 0
        self.status = Cave.IN_PROGRESS ; self.wait = 0
        self.tiles = [] ; self.back_tiles = []
        cave = CAVES[self.level - 1]
        self.miner_type = globals()[cave['miner']] if 'miner' in cave else Miner
        self.height = len(cave['map'])
        self.width = len(cave['map'][0])
        self.to_collect = cave['goal']
        for y in range(self.height):
            self.back_tiles.append([None for _ in range(self.width)])
            self.tiles.append([])
            for x in range(self.width):
                key = cave['map'][self.height -1 - y][x]
                tile_type = types[key] if key in types else Unknown
                tile = tile_type(self, x, y) if not tile_type is None else None
                self.tiles[y].append(tile)
        for sprite in self.sprites(): sprite.on_loaded()
        self.game.on_loaded()
    
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
        self.wait = Cave.WAIT_STATUS

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

    def can_move(self, sprite: 'Sprite', ix: int , iy: int) -> bool:
        (x, y) = (sprite.x + ix, sprite.y + iy)
        if not self.within_bounds(x,y): return False
        tile = self.at(x,y)
        return tile is None or tile.can_be_occupied(sprite, ix, iy)

    def try_move(self, sprite: 'Sprite', ix: int , iy: int) -> bool:
        if not sprite.can_move(ix, iy): return False
        if (ix, iy) == (0, 0) and self.at(sprite.x, sprite.y) is sprite: return True
        if self.at(sprite.x, sprite.y) is sprite: self.set(sprite.x, sprite.y, None)
        sprite.x += ix ;  sprite.y += iy
        tile = self.set(sprite.x, sprite.y, sprite)
        sprite.on_moved(tile)
        if tile is not None and self.at(sprite.x, sprite.y) != tile: tile.on_destroy()
        return True

    def sprites(self, cond: Optional[Union[int,type]] = None) -> Generator['Sprite', None, None]:
        for row in self.tiles:
            for tile in row:
                if tile is not None and tile.is_kind_of(cond): yield tile

    def back_sprites(self, cond: Optional[Union[int,type]] = None) -> Generator['Sprite', None, None]:
        for row in self.back_tiles:
            for tile in row:
                if tile is not None and tile.is_kind_of(cond): yield tile

    def on_update(self, delta_time) -> None:
        if self.wait > 0:
            self.wait -= delta_time
            if self.wait <= 0:
                if self.status == Cave.SUCCEEDED: self.next_level()
                elif self.status == Cave.FAILED: self.restart_level()
        for priority in [Sprite.PRIORITY_HIGH, Sprite.PRIORITY_MEDIUM, Sprite.PRIORITY_LOW]:
            for sprite in self.sprites(priority): sprite.on_update(delta_time)
        for update in Sprite.global_updates: update(self)

    def explode(self, cx: int, cy: int, tile_type: Optional[type] = None) -> None:
        if tile_type is None: tile_type = Explosion
        tile_type.sound_explosion.play()
        for x in range(cx - 1, cx + 2):
            for y in range(cy - 1, cy + 2):
                if self.within_bounds(x, y):
                    tile = self.at(x, y)
                    if tile is None or (not isinstance(tile, tile_type) and tile.can_break()):
                        self.set(x, y, tile_type(self, x, y))
                        if not tile is None: tile.on_destroy()

class CaveView(arcade.View):
    ''' The main view of the game when in play. Renders the current cave. Manages cameras. '''

    def __init__(self, game: 'Game') -> None:
        super().__init__(game)
        self.game = game
        self.camera = None
        self.camera_gui = None
        self.center = None
        self.sprite_list = arcade.SpriteList()

    def on_show_view(self)  -> None:
        self.on_resize(self.window.width, self.window.height)
        self.on_loaded()

    def on_resize(self, width: int, height: int) -> None:
        if self.camera is None or self.camera.viewport_width != width or self.camera.viewport_height != height:
            self.camera = arcade.Camera(width, height)
            self.camera_gui = arcade.Camera(width, height)
            if not self.center is None: self.center_on(*self.center)
            gui_offset = Game.TILE_SIZE if height > (Cave.HEIGHT_MAX + 1) * Game.TILE_SIZE else 0
            self.camera_gui.move_to( ((Game.WIDTH - width)/2, gui_offset))

    def center_on(self, x, y, speed = 1) -> None:
        self.center = (x, y) ; cave = self.game.cave 
        width = self.window.width ; height = self.window.height
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
        y = self.window.height - 7/8 * Game.TILE_SIZE
        arcade.draw_text(text, x*Game.TILE_SIZE, y, color, Game.TILE_SIZE, w * Game.TILE_SIZE, align, Game.FONT)

    def on_draw(self) -> None:
        #start_time = time.time()
        self.camera.use()
        self.clear()
        self.sprite_list.draw() # pixelated = True
        self.camera_gui.use()
        arcade.draw_lrtb_rectangle_filled(0, self.window.width, self.window.height, self.window.height - Game.TILE_SIZE, (0,0,0,192))
        self.print( 0, 4, 'LEVEL') ; self.print( 0, -4, f'{self.game.cave.level:02}')
        self.print( 5, 3, 'LIFE')  ; self.print( 5, -3, f'{self.game.players[0].life:01}')
        self.print( 9, 5, 'GOAL')  ; self.print( 9, -5, f'{self.game.cave.collected:02}/{self.game.cave.to_collect:02}')
        self.print(15, 5, 'SCORE') ; self.print(15, -5, f'{self.game.players[0].score:04}')
        #print(f'on_draw : {(time.time() - start_time) * 1000} ms')

    def on_loaded(self) -> None:
        self.sprite_list.clear()

    def on_update(self, delta_time):
        #start_time = time.time()
        self.game.cave.on_update(delta_time)
        cave_sprites = { *self.game.cave.back_sprites(), *self.game.cave.sprites() }
        for s in self.sprite_list:
            if not s in cave_sprites: self.sprite_list.remove(s)
        for s in cave_sprites:             
            if len(s.sprite_lists) == 0: self.sprite_list.append(s)
        self.sprite_list.sort(key=lambda x: not isinstance(x, BackSprite))
        #print(f'on_update : {(time.time() - start_time) * 1000} ms')

class Game(arcade.Window):
    ''' The main Boulder Dash game. Holds the game model. Manages views. Buffers keys and controllers. '''

    TILE_SIZE = 40
    WIDTH_TILES = Cave.WIDTH_MIN # Cave.WIDTH_MAX
    HEIGHT_TILES = Cave.HEIGHT_MIN # Cave.HEIGHT_MAX
    WIDTH = TILE_SIZE * WIDTH_TILES
    HEIGHT = TILE_SIZE * (HEIGHT_TILES + 1)
    TITLE = 'Boulder Dash'
    FONT = 'Kenney High Square'
    music = Sound(':resources:music/funkyrobot.mp3')
    sound_over = Sound(':resources:sounds/gameover3.wav')

    def __init__(self):
        super().__init__(Game.WIDTH, Game.HEIGHT, Game.TITLE)
        self.set_icon(pyglet.image.load(f'res/Miner{Sprite.TILE_SIZE}-0.png'))
        self.keys = []
        self.controllers = []
        self.players = []
        self.cave = None

    def create_players(self, nb_players: Optional[int] = None) -> None : 
        if nb_players is None: nb_players = len(self.players)
        if nb_players < 1: nb_players = 1
        if nb_players > 4: nb_players = 4
        self.players = [ Player(self, i) for i in range(nb_players) ]
    
    def setup(self) -> None:
        self.controllers = arcade.get_game_controllers()
        for ctrl in self.controllers: ctrl.open()
        self.create_players() ; self.cave = Cave(self)
        arcade.set_background_color(arcade.color.BLACK)
        self.show_view(CaveView(self))
        Game.music.play(0.1, 0, True)

    def center_on(self, x, y, speed = 1) -> None:
        if self.current_view is not None:self.current_view.center_on(x, y, speed)
    def on_loaded(self) -> None:
        if self.current_view is not None: self.current_view.on_loaded()

    def on_key_press(self, symbol, modifiers): 
        self.keys.append(symbol)
        if symbol == arcade.key.NUM_ADD : self.cave.next_level()
        elif symbol == arcade.key.NUM_SUBTRACT : self.cave.next_level(self.cave.level - 1)
        elif (symbol == arcade.key.NUM_MULTIPLY or symbol == arcade.key.F5):
            self.create_players() ; self.cave.restart_level()
        elif symbol == arcade.key.NUM_DIVIDE : 
            self.create_players(len(self.players) % 4 + 1) ; self.cave.restart_level()
        elif (symbol == arcade.key.ENTER or symbol == arcade.key.F11 or (symbol == arcade.key.ESCAPE and self.fullscreen) ):
           self.set_fullscreen(not self.fullscreen)

    def on_key_release(self, symbol, modifiers):
        if symbol in self.keys: self.keys.remove(symbol)

    def over(self) -> None:
        Game.sound_over.play()

def main() -> None:
    Game().setup()
    arcade.run()

if __name__ == '__main__':
    main()
