import arcade
import random
from typing import Optional
from boulder_dash import Game, Player
from collections import namedtuple

TILE_SIZE = 64
TILE_SCALE = 0.5
DEFAULT_SPEED = 16 # squares per second
KEY_UP = 0
KEY_LEFT = 1
KEY_DOWN = 2
KEY_RIGHT = 3

Direction = namedtuple('Direction', 'x y')

class Element(arcade.Sprite):
    def __init__(self, game: Game, x: int, y: int, n: int = 1) -> None:
        super().__init__(None, TILE_SCALE)
        for i in range(0, n): 
            self.append_texture(arcade.load_texture("Tiles/" + type(self).__name__ + str(TILE_SIZE) + "-" + str(i) + ".png"))
        if n > 0: self.set_texture(0)
        self.game = game
        self.x = x ; self.y = y;
        self.wait = 0 ; self.speed = DEFAULT_SPEED
        self.moved = self.moving = False
        self.compute_pos()
    
    def compute_pos(self) -> None:
        self.center_x = TILE_SIZE * TILE_SCALE * (self.x + 0.5)
        self.center_y = TILE_SIZE * TILE_SCALE * (self.y + 0.5)

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
    def can_be_penetrated(self, by: "Element") -> bool: return False
    def on_moved(self, into: Optional["Element"]) -> None: pass
    def can_break(self) -> bool:  return True
    def on_destroy(self) -> None: pass

class Unknown(Element):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class Soil(Element):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)
    def can_be_penetrated(self, by: Element) -> bool: return isinstance(by, Miner)

class Wall(Element):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class BrickWall(Wall):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class MetalWall(Wall):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)
    def can_break(self) -> bool:  return False

class Ore(Element):
    def __init__(self, game: Game, x: int, y: int, n:int = 1) -> None: super().__init__(game, x, y, n)

    def tick(self) -> None:
        if self.try_move(0, -1): return
        ix = random.randint(0, 1) * 2 - 1;  # pick a side at random
        self.try_roll(ix) or self.try_roll(-ix)

    def try_roll(self, ix: int) -> bool:
        below = self.game.cave.at(self.x, self.y -1)
        return (isinstance(below, Ore) or isinstance(below, Wall)) and self.can_move(ix, -1) and self.try_move(ix, 0)

class Boulder(Ore):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class Diamond(Ore):
    def __init__(self, game: Game, x: int, y: int) -> None:
       super().__init__(game, x, y, 4)
       self.game.cave.to_collect += 1

    def can_be_penetrated(self, by: Element) -> bool: return isinstance(by, Miner)
    def can_break(self) -> bool:  return False

    def on_destroy(self) -> None:
       self.game.cave.to_collect -= 1

    def tick(self) -> None:
        shine = random.randint(1, 40)
        if shine > 3: shine = 0
        self.set_texture(shine)
        super().tick()

class Explosion(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.wait = 1/8
    def can_be_penetrated(self, by: Element) -> bool: return True
    def tick(self) -> None: self.game.cave.replace(self, None)

class Entry(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y, 0)
        self.append_texture(arcade.load_texture("Tiles/" + MetalWall.__name__ + str(TILE_SIZE) + "-0.png"))
        self.set_texture(0)
        self.wait = 1/2
        self.player = self.game.players[self.game.cave.nb_players]
        self.game.cave.nb_players += 1

    def tick(self) -> None:
        if self.player.life > 0: self.game.cave.replace(self, Miner(self.game, self.x, self.y, self.player)); 
        else: self.game.cave.replace(self, None)

class Exit(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.append_texture(arcade.load_texture("Tiles/" + MetalWall.__name__ + str(TILE_SIZE) + "-0.png"))
        self.opened = False ; self.set_texture(1)

    def tick(self) -> None:
        if self.game.cave.complete() :
            self.opened = True ; self.set_texture(0)

    def can_be_penetrated(self, by: Element) -> bool: 
        return isinstance(by, Miner) and self.opened
    
    def on_destroy(self) -> None: self.game.cave.next_level()

class Character(Element):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)
    def can_be_penetrated(self, by: Element) -> bool: return (isinstance(by, Ore) and by.moving)
    def on_destroy(self) -> None: self.game.cave.explode(self.x, self.y)

class Miner(Character):
    def __init__(self, game: Game, x: int, y: int, player: Player) -> None:
        super().__init__(game, x, y)
        self.pushing = 0
        self.player = player

    def can_be_penetrated(self, by: Element) -> bool:
        return super().can_be_penetrated(by) or isinstance(by, Firefly)

    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Diamond): self.player.score += 1
        self.pushing = 0

    def pressed(self, key: int) -> bool:
        return self.player.controls[key] in self.game.keys

    def tick(self) -> None:
        if   self.pressed(KEY_LEFT):  
            if not self.try_move(-1, 0): self.try_push(-1)
        elif self.pressed(KEY_RIGHT):
            if not self.try_move(+1, 0): self.try_push(+1)
        elif self.pressed(KEY_UP):
            self.try_move(0, +1)
        elif self.pressed(KEY_DOWN):
            self.try_move(0, -1)
    
    def try_push(self, ix: int) -> bool:
        pushed = self.game.cave.at(self.x + ix, self.y)
        if not isinstance(pushed, Boulder): return False
        if self.pushing != ix: 
           self.pushing = ix; self.wait = 1 / self.speed
           return False
        if pushed.try_move(ix, 0): return self.try_move(ix, 0)
        return False

    def on_destroy(self) -> None:
        super().on_destroy()
        self.player.kill()

class Firefly(Character):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.speed /= 2 ; self.dir = Direction(-1, 0)

    def can_be_penetrated(self, by: Element) -> bool:
        return super().can_be_penetrated(by) or isinstance(by, Miner)

    def tick(self) -> None:
        # if in wide 3x3 open area, go straight
        if self.can_move(-1,0) and self.can_move(1,0) and self.can_move(0,-1) and self.can_move(0,1) \
           and self.can_move(-1,-1) and self.can_move(1,-1) and self.can_move(-1,1) and self.can_move(1,1):
               self.try_move(*self.dir)
        # else follow the right wall...
        elif self.try_move(self.dir.y, -self.dir.x):
            self.dir = Direction(self.dir.y, -self.dir.x)
        elif self.try_move(*self.dir):
            pass # go straight
        elif self.try_move(-self.dir.y, self.dir.x):
            self.dir = Direction(-self.dir.y, self.dir.x)
        elif self.try_move(-self.dir.x, -self.dir.y):
            self.dir = Direction(-self.dir.x, -self.dir.y)

class Butterfly(Firefly):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.game.cave.to_kill += 1

    def on_destroy(self) -> None: 
        self.game.cave.explode(self.x, self.y, Diamond)
        self.game.cave.to_kill -= 1