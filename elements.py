import arcade
import random
from typing import Optional, Union
from boulder_dash import Game, Cave, Player

class Sound(arcade.Sound):
    def __init__(self, file): 
        super().__init__(file)
        self.play().delete() # force audio preloading

class Element(arcade.Sprite):
    TILE_SIZE = 16 # 64
    TILE_SCALE = Game.TILE_SIZE / TILE_SIZE
    DEFAULT_SPEED = 15 # squares per second
    PRIORITY_HIGH = 0
    PRIORITY_MEDIUM = 1
    PRIORITY_LOW = 2

    def __init__(self, game: Game, x: int, y: int, n: int = 1) -> None:
        super().__init__(None, Element.TILE_SCALE)
        self.nb_skins = 0
        for i in range(0, n): self.add_skin(type(self).__name__, i)
        if n > 0: self.set_skin(0)
        self.game = game
        self.x = x ; self.y = y;
        self.wait = 0 ; self.speed = Element.DEFAULT_SPEED
        self.moved = self.moving = False ; self.priority = Element.PRIORITY_MEDIUM
        self.compute_pos()

    def add_skin(self, name: str, id: int, flip_h: bool = False, flip_v: bool = False) -> None: 
        self.append_texture(arcade.load_texture(f'Tiles/{name}{Element.TILE_SIZE}-{id}.png', 0,0, Element.TILE_SIZE, Element.TILE_SIZE, flip_h, flip_v))
        self.nb_skins += 1
    def set_skin(self, i: int) -> None: self.skin = i; self.set_texture(i)
    def next_skin(self) -> None: self.set_skin( (self.skin+1) % self.nb_skins )
     
    def compute_pos(self) -> None:
        self.center_x = Element.TILE_SIZE * Element.TILE_SCALE * (self.x + 0.5)
        self.center_y = Element.TILE_SIZE * Element.TILE_SCALE * (self.y + 0.5)

    def neighbor(self, ix:int, iy:int) -> Optional['Element'] :
        return self.game.cave.at(self.x + ix, self.y + iy)

    def is_kind_of(self, cond: Optional[Union[int, type]]):
        return cond is None or (isinstance(cond, type) and isinstance(self, cond)) or self.priority == cond

    def can_move(self, ix: int, iy: int)  -> bool:
        return self.game.cave.can_move(self, self.x + ix, self.y + iy)

    def try_move(self, ix: int, iy: int)  -> bool:
        if self.game.cave.try_move(self, self.x + ix, self.y + iy):
            self.compute_pos()
            self.wait = 1 / self.speed
            self.moved = True
            return True
        return False

    def on_update(self, delta_time) -> None:
        if self.wait > 0: 
            self.wait -= delta_time
        else: 
            self.moved = False
            self.tick() 
            self.moving = self.moved

    def tick(self): pass
    def can_be_penetrated(self, by: 'Element') -> bool: return False
    def on_moved(self, into: Optional['Element']) -> None: pass
    def can_break(self) -> bool:  return True
    def on_destroy(self) -> None: pass

class Unknown(Element):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class Soil(Element):
    sound = Sound(":resources:sounds/rockHit2.wav")
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)
    def can_be_penetrated(self, by: Element) -> bool: return isinstance(by, Miner)
    def collect(self) -> int : Soil.sound.play() ; return 0

class Wall(Element):
    def __init__(self, game: Game, x: int, y: int, n: int = 1) -> None: super().__init__(game, x, y, n)

class BrickWall(Wall):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class MetalWall(Wall):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)
    def can_break(self) -> bool:  return False

class ExpandingWall(Wall):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y, 2)
        self.add_skin(ExpandingWall.__name__, 1, True)
        self.wait = 2 / Element.DEFAULT_SPEED

    def tick(self) -> None:
        self.set_skin(0)
        for ix in [-1,+1]:
            if self.neighbor(ix, 0) is None:
                tile = ExpandingWall(self.game, self.x+ix, self.y)
                tile.set_skin(2 if ix == -1 else 1)
                self.game.cave.tiles[self.y][self.x+ix] = tile
                self.wait = 2 / Element.DEFAULT_SPEED
                Boulder.sound_fall.play()

class Ore(Element):
    def __init__(self, game: Game, x: int, y: int, n:int = 1) -> None: 
        super().__init__(game, x, y, n)

    def tick(self) -> None:
        if self.try_move(0, -1): return
        elif self.moving: type(self).sound_fall.play()
        ix = random.randint(0, 1) * 2 - 1;  # pick a side at random
        self.try_roll(ix) or self.try_roll(-ix)
    
    def try_roll(self, ix: int) -> bool:
        below = self.neighbor(0, -1)
        return (isinstance(below, Ore) or isinstance(below, BrickWall)) and self.can_move(ix, -1) and self.try_move(ix, 0)

class Boulder(Ore):
    sound = Sound(":resources:sounds/hurt1.wav")
    sound_fall = Sound(":resources:sounds/hurt2.wav")
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class Diamond(Ore):
    sound = Sound(":resources:sounds/coin5.wav")
    sound_fall = Sound(":resources:sounds/coin4.wav")
    sound_explosion = Sound(":resources:sounds/secret4.wav")
    def __init__(self, game: Game, x: int, y: int) -> None:
       super().__init__(game, x, y, 4)

    def can_be_penetrated(self, by: Element) -> bool: return isinstance(by, Miner)
    def can_break(self) -> bool:  return False

    def collect(self) -> int: 
        Diamond.sound.play()
        self.game.cave.collected += 1
        return 5 if self.game.cave.is_complete() else 2

    def tick(self) -> None:
        if random.randint(0,2) == 1:
            shine = random.randint(1, 40)
            if shine > 3: shine = 0
            self.set_skin(shine)
        super().tick()

class Explosion(Element):
    sound_explosion = Sound(":resources:sounds/explosion2.wav")
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.wait = .125 # seconds
    def can_be_penetrated(self, by: Element) -> bool: return True
    def tick(self) -> None: self.game.cave.replace(self, None)

class Entry(Element):
    sound = Sound(":resources:sounds/jump4.wav")
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y, 0)
        self.add_skin(Exit.__name__, 1)
        self.set_skin(0)
        self.wait = 0.75 # seconds
        self.player = self.game.players[self.game.cave.nb_players]
        self.game.cave.nb_players += 1
        self.game.center_on(self.center_x, self.center_y)

    def tick(self) -> None:
        if self.player.life > 0: 
            Entry.sound.play()
            self.game.cave.replace(self, Miner(self.game, self.x, self.y, self.player)); 

class Exit(Element):
    sound = Sound(":resources:sounds/upgrade1.wav")
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y, 2)
        self.opened = False

    def tick(self) -> None:
        if not self.opened and self.game.cave.is_complete() :
            Entry.sound.play()
            self.opened = True ; self.set_skin(1)

    def can_be_penetrated(self, by: Element) -> bool: 
        return isinstance(by, Miner) and self.opened
    def can_break(self) -> bool:  return False

    def on_destroy(self) -> None: 
        Exit.sound.play()
        self.game.cave.set_status(Cave.SUCCEEDED)

class Character(Element):
    def __init__(self, game: Game, x: int, y: int, n: int = 1) -> None:
       super().__init__(game, x, y, n)
       self.dir = (0, 0)

    def try_dir(self, ix: int, iy: int) -> bool:
        if self.try_move(ix, iy): self.dir = (ix, iy) ; return True
        else: return False

    def can_be_penetrated(self, by: Element) -> bool: 
        return isinstance(by, Ore) and by.moving

    def on_destroy(self) -> None: self.game.cave.explode(self.x, self.y)

class Miner(Character):
    def __init__(self, game: Game, x: int, y: int, player: Player) -> None:
        super().__init__(game, x, y)
        self.pushing = None
        self.player = player
        self.priority = Element.PRIORITY_HIGH

    def can_be_penetrated(self, by: Element) -> bool:
        return ( 
            self.game.cave.status == Cave.IN_PROGRESS and
            (super().can_be_penetrated(by) or isinstance(by, Firefly))
        )

    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Diamond) or isinstance(into, Soil):
            self.player.score += into.collect()
        self.pushing = None

    def on_update(self, delta_time) -> None:
        super().on_update(delta_time)
        if self.moved: self.player.center_on(self.center_x, self.center_y)

    def tick(self) -> None:
        if self.game.cave.status != Cave.IN_PROGRESS: return
        for dir in [(-1,0),(+1,0),(0,-1),(0,+1)]:
            if self.player.is_direction(*dir):
                if self.try_dir(*dir): return
        for dir in [(-1,0),(+1,0)]:
            if self.player.is_direction(*dir):
                if self.try_push(*dir): return

    def try_push(self, ix:int, iy:int) -> bool:
        if ix != 0 and iy == 0:
            pushed = self.neighbor(ix, iy)
            if isinstance(pushed, Boulder):
                if self.pushing == (ix, iy):
                    if pushed.try_move(ix, iy): 
                        Boulder.sound.play()
                        return self.try_dir(ix, iy)
                else:
                    self.dir = (ix, iy)
                    self.pushing = self.dir; self.wait = 1 / self.speed
        return False

    def on_destroy(self) -> None:
        super().on_destroy()
        self.player.kill()

class Firefly(Character):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y, 2)
        self.speed /= 2 ; self.dir = (-1, 0)
        self.priority = Element.PRIORITY_LOW

    def can_be_penetrated(self, by: Element) -> bool:
        return super().can_be_penetrated(by) or isinstance(by, Miner)

    def try_wander(self) -> bool:
        (ix,iy) = self.dir
        # always go left
        return self.try_dir(-iy, ix) or self.try_dir(ix, iy) or self.try_dir(iy, -ix) or self.try_dir(-ix, -iy)
    
    def tick(self) -> None:
        self.next_skin()
        # if adjacent to a miner, try to catch him
        for look in [(-1,0),(+1,0),(0,-1),(0,+1)]:
            if isinstance(self.neighbor(*look), Miner) and self.try_dir(*look): return
        # else wander around
        self.try_wander()

class Butterfly(Firefly):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.dir = (0, -1)

    def try_wander(self) -> bool:
        (ix,iy) = self.dir
        # always go right
        return self.try_dir(iy, -ix) or self.try_dir(ix, iy) or self.try_dir(-iy, ix) or self.try_dir(-ix, -iy)

    def on_destroy(self) -> None: self.game.cave.explode(self.x, self.y, Diamond)

class MagicWall(Wall): 
    # TODO ? don't inherit from wall, to prevent Ore from rolling ? (I don't like this rule)
    def __init__(self, game: Game, x: int, y: int) -> None:
       super().__init__(game, x, y, 3)
       self.add_skin(BrickWall.__name__, 0)

    def tick(self) -> None:
        if random.randint(0, 6) == 0: self.set_skin(random.randint(0, self.nb_skins - 1))
        super().tick()

    def can_be_penetrated(self, by: 'Element') -> bool:
        return isinstance(by, Ore) and by.moving

    def on_destroy(self) -> None:
        # won't be destroyed by falling ore, do its magic instead !
        ore = self.game.cave.at(self.x, self.y)
        if isinstance(ore, Ore): 
            ore = Boulder(self.game, self.x, self.y) if isinstance(ore, Diamond) else Diamond(self.game, self.x, self.y)
            ore.tick() # continue its fall through...
            self.game.cave.tiles[self.y][self.x] = self

class Amoeba(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.DEFAULT_SPEED = 2
        self.add_skin(Amoeba.__name__, 0, True, False) ; self.add_skin(Amoeba.__name__, 0, False, True) ; self.add_skin(Amoeba.__name__, 0, True, True) 
        self.set_skin(random.randint(0, self.nb_skins - 1))
        self.wait = 1 / self.DEFAULT_SPEED
        self.trapped = False

    def tick(self) -> None:
        if random.randint(0, 7) == 0: self.set_skin(random.randint(0, self.nb_skins - 1))
        self.trapped = True
        for look in [[-1,0], [+1,0], [0,-1], [0,+1]]:
            if self.neighbor(look[0], look[1]) == None :
                self.trapped = False
                if random.randint(0, 3) == 0:
                    self.game.cave.tiles[self.y+look[1]][self.x+look[0]] = Amoeba(self.game, self.x+look[0], self.y+look[1])
            elif isinstance(self.neighbor(look[0], look[1]), Soil) :
                self.trapped = False
                if random.randint(0, 31) == 0:
                    self.game.cave.tiles[self.y+look[1]][self.x+look[0]] = Amoeba(self.game, self.x+look[0], self.y+look[1])
        self.wait = 1 / self.DEFAULT_SPEED