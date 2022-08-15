from typing import Optional, Union, Tuple, List, Iterable
from collections import namedtuple
import time
import math
import pyglet
import arcade

class Sound:
    ''' An audio media in the game. Played at moderate volume and at most once per frame (for a given sound). '''
    VOLUME = 0.5
    MAX_RATE = 1/60 # sec

    def __init__(self, file: str) -> None:
        self.file = file ; self.media = None ; self.last_played = -math.inf
        #self.load() # force audio preloading (is it necessary ?)

    def load(self) -> None: 
        if self.media is None:
            #print('Loading sound ' + self.file, end = '', flush = True)
            self.media = arcade.Sound(self.file)
            #self.media.play(0).delete() # force audio preloading (is it necessary ?)
            #print(' ...')

    def play(self, volume = VOLUME, pan: float = 0.0, loop: bool = False, speed: float = 1.0):
        if self.media is None: self.load()
        now = time.time()
        if (now - self.last_played < Sound.MAX_RATE): return None
        self.last_played = now
        return self.media.play(volume, pan, loop, speed)

class Interface:
    ''' Pure abstract. To distinguish from standard classes. '''

class Tile(arcade.Sprite):
    ''' A tile in the game's cave. Manages skins, positioning, basic movement, timings, and update. '''

    TILE_SIZE = 64 # choose from 16, 64
    DEFAULT_SPEED = 10 # squares per second
    PRIORITY_HIGH = 0
    PRIORITY_MEDIUM = 1
    PRIORITY_LOW = 2

    registered_tiles = {}
    global_updates = []
    def __init__(self, cave: 'Cave', x: int, y: int, n: int = 1) -> None:
        super().__init__(None, Game.TILE_SIZE / Tile.TILE_SIZE)
        self.nb_skins = 0 ; self.skin = None
        for i in range(n): self.add_skin(type(self), i)
        self.cave = cave ; self.back = False ; self.x = x ; self.y = y ; self.dir = (0, 0)
        self.wait = 0 ; self.speed = Tile.DEFAULT_SPEED
        self.moved = self.moving = False ; self.priority = Tile.PRIORITY_MEDIUM
        self.compute()

    def add_skin(self, kind: Union[str, type], num: int, flip_h: bool = False, flip_v: bool = False) -> None: 
        name = kind.__name__ if isinstance(kind, type) else kind
        file_name = f'res/{name}{Tile.TILE_SIZE}-{num}.png'
        try:
            texture = arcade.load_texture(file_name, 0,0, Tile.TILE_SIZE, Tile.TILE_SIZE, flip_h, flip_v)
            self.append_texture(texture) ; self.nb_skins += 1
            if self.nb_skins == 1: self.set_skin(0)
        except FileNotFoundError as err:
            if isinstance(kind, type) and len(kind.__bases__) > 0:
                self.add_skin(kind.__bases__[0], num, flip_h, flip_v)
            else: raise err
    def set_skin(self, i: int) -> None: self.skin = i; self.set_texture(i)
    def next_skin(self) -> None: self.set_skin( (self.skin+1) % self.nb_skins )

    def compute(self) -> None:
        self.center_x = Game.TILE_SIZE * (self.x + 0.5)
        self.center_y = Game.TILE_SIZE * (self.y + 0.5)
    def focus(self, speed = 1) -> None:
        self.cave.game.center_on(self.center_x, self.center_y, speed)

    def pos(self, _observer: Optional['Tile'], _ix: int, _iy: int) -> Tuple[int,int]:
        return (self.x ,self.y)
    def offset(self, ix: int, iy: int) -> Tuple[int,int]:
        (x, y) = self.cave.wrap(self.x + ix ,self.y + iy) ; tile = self.cave.at(x, y)
        return (x, y) if tile is None else tile.pos(self, ix, iy)
    def neighbor(self, ix: int, iy: int) -> Optional['Tile'] :
        return self.cave.at(*self.offset(ix,iy))

    def is_kind_of(self, cond: Optional[Union[int, type]]):
        return cond is None or (isinstance(cond, type) and isinstance(self, cond)) or self.priority == cond

    def can_move(self, ix: int, iy: int)  -> bool:
        return self.cave.can_move(self, ix, iy)

    def try_move(self, ix: int, iy: int) -> bool:
        self.dir = (ix, iy)
        if self.cave.try_move(self, ix, iy):
            self.compute() ; self.moved = True
            return self.try_wait()
        return False

    def try_wait(self) -> bool:
        self.wait = 1 / self.speed
        return True

    def on_update(self, delta_time: float = 1/60) -> None:
        if self.wait > 0:  self.wait -= delta_time
        else: self.moved = False ; self.tick() ; self.moving = self.moved

    def tick(self): pass
    def can_be_occupied(self, _by: 'Tile', _ix: int, _iy: int) -> bool: return False
    def on_moved(self, _into: Optional['Tile']) -> None: pass
    def can_break(self) -> bool:  return True
    def on_destroy(self) -> None: pass
    def on_loaded(self) -> None: pass

class Unknown(Tile):
    ''' Typically used to represent a tile not yet implemented. '''
    def __init__(self, cave: 'Cave', x: int, y: int) -> None: super().__init__(cave, x, y)

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

    def list_directions(self) -> List[Tuple[int,int]]:
        dirs = []
        for key in self.game.keys:
            direction = self.key_direction(key)
            if direction is not None: dirs.insert(0, direction)
        for direction in [(-1,0),(+1,0),(0,-1),(0,+1)]:
            if not direction in dirs and self.is_ctrl_direction(*direction): 
                dirs.append(direction)
        return dirs

    def key_direction(self, key) -> Optional[Tuple[int,int]]:
        if   key == self.control_keys.up    : return (0,+1)
        elif key == self.control_keys.left  : return (-1,0)
        elif key == self.control_keys.down  : return (0,-1)
        elif key == self.control_keys.right : return (+1,0)
        else: return None

    def is_ctrl_direction(self, ix: int, iy: int) -> Tuple[int,int]:
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
        else: 
            self.game.cave.set_status(Cave.GAME_OVER)
            self.game.over()

class Geometry:
    ''' Defines how the space wraps around. By default, it doesn't. '''
    def wrap(self, x: int, y: int, _w:int, _h: int) -> Tuple[int,int] : return (x, y)

class Torus(Geometry):
    ''' On a torus, opposite sides are identified. '''
    def wrap(self, x: int, y: int, w:int, h: int) -> Tuple[int,int] : return (x%w, y%h)

class Cave:
    ''' The grid of tiles in which the game is played. Manages map loading and tiles updates. '''

    WIDTH_MAX = 40
    WIDTH_MIN = 20
    HEIGHT_MAX = 22
    HEIGHT_MIN = 12

    STARTING = 0
    IN_PROGRESS = 1
    PAUSED = 2
    SUCCEEDED = 3
    NOT_LOADED = -1
    FAILED = -2
    GAME_OVER = -3

    WAIT_STATUS = 0.75 # seconds
    DEFAULT_MAXTIME = 120 # seconds

    from caves import CAVES

    def __init__(self, game: 'Game') -> None:
        self.game = game
        self.to_collect = 0 ; self.collected = 0
        self.status = Cave.NOT_LOADED ; self.wait = 0
        self.front_tiles = [] ; self.back_tiles = []
        self.miner_type = None ; self.geometry = None
        self.height = self.width = 0
        self.time_remaining = 0
        self.next_level(1)

    def load(self) -> None:
        types = { ' ': None, '_': None, **Tile.registered_tiles } 
        self.to_collect = 0 ; self.collected = 0
        if self.status != Cave.GAME_OVER: self.status = Cave.STARTING    
        self.wait = 0
        self.front_tiles = [] ; self.back_tiles = []
        cave = Cave.CAVES[self.level - 1]
        type_name = cave['miner'] if 'miner' in cave else 'Miner'
        self.miner_type = next(value for (_, value) in types.items() if value is not None and value.__name__ == type_name)
        self.height = len(cave['map'])
        self.width = len(cave['map'][0])
        self.to_collect = cave['goal']
        self.geometry = globals()[cave['geometry']]() if 'geometry' in cave else Geometry()
        self.time_remaining = cave['time'] if 'time' in cave else Cave.DEFAULT_MAXTIME
        for y in range(self.height):
            self.back_tiles.append([None for _ in range(self.width)])
            self.front_tiles.append([])
            for x in range(self.width):
                key = cave['map'][self.height -1 - y][x]
                tile_type = types[key] if key in types else Unknown
                tile = tile_type(self, x, y) if not tile_type is None else None
                self.front_tiles[y].append(tile)
        for tile in self.tiles(): tile.on_loaded()
        self.game.on_loaded()

    def next_level(self, level : Optional[int] = None) -> None:
        self.level = self.level + 1 if level is None else level
        if self.level < 1 : self.level += len(Cave.CAVES)
        elif self.level > len(Cave.CAVES) : self.level -= len(Cave.CAVES)
        self.load()

    def restart_level(self) -> None: self.next_level(self.level)

    def is_complete(self) -> bool:
        return self.collected >= self.to_collect
    
    def pause(self) -> None:
        if self.status == Cave.IN_PROGRESS: self.status = Cave.PAUSED
        elif self.status == Cave.PAUSED: self.status = Cave.IN_PROGRESS

    def set_status(self, status) -> None:
        self.status = status
        self.wait = Cave.WAIT_STATUS

    def wrap(self, x:int, y:int) -> Tuple[int,int]:
        return self.geometry.wrap(x, y, self.width, self.height)

    def within_bounds(self, x: int ,y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def at(self, x: int , y: int, back: bool = False) -> Optional['Tile']:
        (x,y) = self.wrap(x,y)
        tiles_array = self.front_tiles if not back else self.back_tiles
        return tiles_array[y][x] if self.within_bounds(x,y) else None
    
    def set(self, x: int , y: int, tile: Optional['Tile'], back: bool = False) -> Optional['Tile']:
        (x,y) = self.wrap(x,y)
        current = self.at(x, y, back)
        if self.within_bounds(x,y): 
            tiles_array = self.front_tiles if not back else self.back_tiles
            tiles_array[y][x] = tile
        return current

    def replace(self, tile : 'Tile', by : Union['Tile', type, None]) -> None:
        if self.at(tile.x, tile.y) is tile: # still there ?
            self.set(tile.x, tile.y, by(self, tile.x, tile.y) if isinstance(by, type) else by)
            tile.on_destroy()

    def replace_all(self, cond: Optional[Union[int,type]], by: Union['Tile', type, None]) -> None:
        for tile in self.tiles(cond): self.replace(tile, by)

    def can_move(self, actor: 'Tile', ix: int , iy: int) -> bool:
        (x, y) = actor.offset(ix, iy)
        if not self.within_bounds(x, y): return False
        current = self.at(x,y)
        return current is None or current.can_be_occupied(actor, ix, iy)

    def try_move(self, actor: 'Tile', ix: int , iy: int) -> bool:
        if not actor.can_move(ix, iy): return False
        current = self.at(actor.x, actor.y)
        if (ix, iy) == (0, 0) and current is actor: return True
        if current is actor: self.set(actor.x, actor.y, None)
        (actor.x, actor.y) = actor.offset(ix, iy)
        previous = self.set(actor.x, actor.y, actor)
        actor.on_moved(previous)
        if previous is not None and self.at(actor.x, actor.y) != previous: previous.on_destroy()
        return True

    def tiles(self, cond: Optional[Union[int,type]] = None, back: bool = False) -> Iterable['Tile']:
        tiles_array = self.front_tiles if not back else self.back_tiles
        for row in tiles_array:
            for tile in row:
                if tile is not None and tile.is_kind_of(cond): yield tile

    def on_update(self, delta_time) -> None:
        if self.status == Cave.PAUSED: return
        if self.status == Cave.IN_PROGRESS:
            self.time_remaining -= delta_time
            if self.time_remaining <= 0: 
                self.time_remaining = 0 ; self.set_status(Cave.FAILED)
        if self.wait > 0:
            self.wait -= delta_time
            if self.wait <= 0:
                if self.status == Cave.SUCCEEDED: self.next_level()
                elif self.status == Cave.FAILED: self.restart_level()
        for priority in [Tile.PRIORITY_HIGH, Tile.PRIORITY_MEDIUM, Tile.PRIORITY_LOW]:
            for tile in self.tiles(priority): tile.on_update(delta_time)
        for update in Tile.global_updates: update(self)

    def explode(self, cx: int, cy: int, tile_type: type) -> None:
        tile_type.sound_explosion.play()
        for x in range(cx - 1, cx + 2):
            for y in range(cy - 1, cy + 2):
                (x,y) = self.wrap(x,y)
                if self.within_bounds(x, y):
                    tile = self.at(x, y)
                    if tile is None or (not isinstance(tile, tile_type) and tile.can_break()):
                        self.set(x, y, tile_type(self, x, y))
                        if not tile is None: tile.on_destroy()
                    back = self.at(x, y, True)
                    if back is not None and back.can_break(): 
                        self.set(x, y, None, True)
                        back.on_destroy()

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
            gui_offset = Game.TILE_SIZE / 2 if height > (Cave.HEIGHT_MAX + 1) * Game.TILE_SIZE else 0
            self.camera_gui.move_to( ((Game.WIDTH - width)/2, gui_offset))

    def center_on(self, x, y, speed = 1) -> None:
        self.center = (x, y) ; cave = self.game.cave 
        width = self.window.width ; height = self.window.height
        if width > cave.width * Game.TILE_SIZE:
            cx = (cave.width * Game.TILE_SIZE - width) / 2
        else:
            cx = min(max(x - width / 2, 0), cave.width * Game.TILE_SIZE - width)
        if height > (cave.height + 1) * Game.TILE_SIZE:
            cy = ((cave.height + 1) * Game.TILE_SIZE - height) / 2
        else:
            cy = min(max(y - height / 2, 0), (cave.height + 1) * Game.TILE_SIZE - height)
        self.camera.move_to((cx, cy) , speed)

    def print(self, x: int, w: int, text: str) -> None:
        (color, align, w) = (arcade.color.GRULLO, 'left', w) if w >= 0 else (arcade.color.DARK_PASTEL_GREEN, 'right', -w)
        y = self.window.height - Game.TILE_SIZE * 17/16
        arcade.draw_text(text, x*Game.TILE_SIZE, y, color, Game.TILE_SIZE, w * Game.TILE_SIZE, align, Game.FONT, anchor_y = 'bottom')

    def notify(self, text: str, color) -> None:
        arcade.draw_lrtb_rectangle_filled(Game.WIDTH/3, 2/3*Game.WIDTH, self.window.height/2 + Game.TILE_SIZE, self.window.height/2 - Game.TILE_SIZE, (0,0,0,128))
        arcade.draw_lrtb_rectangle_outline(Game.WIDTH/3, 2/3*Game.WIDTH, self.window.height/2 + Game.TILE_SIZE, self.window.height/2 - Game.TILE_SIZE, arcade.color.GRULLO, Game.TILE_SIZE/16)
        arcade.draw_text(text, 0, self.window.height/2 +Game.TILE_SIZE/16, color, Game.TILE_SIZE, Game.WIDTH, 'center', Game.FONT, anchor_y = 'center')

    def on_draw(self) -> None:
        #start_time = time.time()
        self.camera.use()
        self.clear()
        self.sprite_list.draw()
        self.camera_gui.use()
        arcade.draw_lrtb_rectangle_filled(0, self.window.width, self.window.height, self.window.height - Game.TILE_SIZE, (0,0,0,192))
        self.print( 0, 3, 'LVL')   ; self.print( 0, -3, f'{self.game.cave.level:02}')
        self.print( 3.5, 2.5, 'LIFE')  ; self.print( 3.5, -2.5, f'{self.game.players[0].life:01}')
        self.print( 6.5, 3.5, 'TIME')    ; self.print( 6.5, -3.5, f'{math.floor(self.game.cave.time_remaining):03}')
        if self.game.cave.collected <= self.game.cave.to_collect:
            self.print(10.5, 3.5, 'GOAL')    ; self.print(10.5, -3.5, f'{self.game.cave.to_collect-self.game.cave.collected:02}')
        else:
            self.print(10.5, 3.5, 'PLUS')    ; self.print(10.5, -3.5, f'{self.game.cave.collected-self.game.cave.to_collect:02}')
        self.print(14.5, 5.5, 'SCR')   ; self.print(14.5, -5.5, f'{self.game.players[0].score:07}')
        if self.game.cave.status == Cave.NOT_LOADED: self.notify("LOADING", arcade.color.GRULLO)
        elif self.game.cave.status == Cave.PAUSED: self.notify("PAUSED", arcade.color.GRULLO)
        elif self.game.cave.status == Cave.STARTING: self.notify("GET READY", arcade.color.BANANA_YELLOW)
        elif self.game.cave.status == Cave.SUCCEEDED: self.notify("WELL DONE", arcade.color.DARK_PASTEL_GREEN)
        elif self.game.cave.status == Cave.FAILED: self.notify("TRY AGAIN", arcade.color.CADMIUM_ORANGE)
        elif self.game.cave.status == Cave.GAME_OVER: self.notify("GAME OVER", arcade.color.FERRARI_RED)
        #print(f'on_draw : {(time.time() - start_time) * 1000} ms')

    def on_loaded(self) -> None:
        self.sprite_list.clear()

    def on_update(self, delta_time):
        #start_time = time.time()
        self.game.cave.on_update(delta_time)
        cave_tiles = { *self.game.cave.tiles(None, True), *self.game.cave.tiles() }
        for s in self.sprite_list:
            if not s in cave_tiles: self.sprite_list.remove(s)
        for s in cave_tiles:             
            if len(s.sprite_lists) == 0: self.sprite_list.append(s)
        self.sprite_list.sort(key = lambda s: not s.back)
        #print(f'on_update : {(time.time() - start_time) * 1000} ms')

class Game(arcade.Window):
    ''' The main Boulder Dash game. Holds the game model. Manages views. Buffers keys and controllers. '''

    TILE_SIZE = 42 # 64
    WIDTH_TILES = Cave.WIDTH_MIN # Cave.WIDTH_MAX
    HEIGHT_TILES = Cave.HEIGHT_MIN # Cave.HEIGHT_MAX
    WIDTH = TILE_SIZE * WIDTH_TILES
    HEIGHT = TILE_SIZE * (HEIGHT_TILES + 1)
    TITLE = 'Boulder Dash'
    FONT = 'Kenney High Square'

    music = Sound(':resources:music/funkyrobot.mp3')
    sound_over = Sound(':resources:sounds/gameover3.wav')

    def __init__(self):
        super().__init__(Game.WIDTH, Game.HEIGHT, Game.TITLE, vsync = True)
        self.set_icon(pyglet.image.load('res/Miner64-0.png'))
        self.keys = []
        self.controllers = []
        self.players = []
        self.cave = None
        self.music_player = None

    def create_players(self, nb_players: Optional[int] = None) -> None : 
        if nb_players is None: nb_players = len(self.players)
        nb_players = min(max(nb_players, 1), 4)
        self.players = [ Player(self, i) for i in range(nb_players) ]
    
    def setup(self) -> None:
        self.controllers = arcade.get_game_controllers()
        for ctrl in self.controllers: ctrl.open()
        self.create_players() ; self.cave = Cave(self)
        arcade.set_background_color(arcade.color.BLACK)
        self.show_view(CaveView(self))
        #self.toggle_music()
    
    def toggle_music(self) -> None:
        if self.music_player is None: 
            self.music_player = Game.music.play(0.1, 0, True)
            if self.cave.status == Cave.PAUSED: self.music_player.pause()
        else: self.music_player.delete() ; self.music_player = None

    def pause(self) -> None:
        self.cave.pause()
        if self.music_player is not None:
            if self.cave.status == Cave.PAUSED: self.music_player.pause()
            else: self.music_player.play()

    def center_on(self, x, y, speed = 1) -> None:
        if self.current_view is not None: self.current_view.center_on(x, y, speed)

    def on_loaded(self) -> None:
        if self.current_view is not None: self.current_view.on_loaded()

    def on_key_press(self, symbol, modifiers): 
        if not symbol in self.keys: self.keys.append(symbol)
        if symbol == arcade.key.NUM_ADD : self.cave.next_level()
        elif symbol == arcade.key.NUM_SUBTRACT : self.cave.next_level(self.cave.level - 1)
        elif (symbol in (arcade.key.NUM_MULTIPLY, arcade.key.F5)):
            self.create_players() ; self.cave.restart_level()
        elif (symbol in (arcade.key.NUM_DIVIDE, arcade.key.F3)):
            self.create_players(len(self.players) % 4 + 1) ; self.cave.restart_level()
        elif (symbol in (arcade.key.ENTER, arcade.key.F11) or (symbol == arcade.key.ESCAPE and self.fullscreen) ):
            self.set_fullscreen(not self.fullscreen)
        elif symbol == arcade.key.F9: self.toggle_music()
        elif symbol == arcade.key.SPACE: self.pause()

    def on_key_release(self, symbol, modifiers):
        if symbol in self.keys: self.keys.remove(symbol)

    def over(self) -> None:
        Game.sound_over.play()

def main() -> None:
    Game().setup()
    arcade.run()

if __name__ == '__main__':
    import tiles
    import custom_tiles
    tiles.register(Tile)
    custom_tiles.register(Tile)
    main()
