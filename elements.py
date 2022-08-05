import arcade
import random
from typing import Optional
from boulder_dash import Game

TILE_SIZE = 64
TILE_SCALE = 0.5
DEFAULT_SPEED = 8 # squares per second
KEY_UP = 0
KEY_LEFT = 1
KEY_DOWN = 2
KEY_RIGHT = 3

class Element(arcade.Sprite):
    def __init__(self, game: Game, x: int, y: int, n: int = 0) -> None:
        super().__init__("Tiles/" + type(self).__name__ + str(TILE_SIZE) + "-0.png", TILE_SCALE)
        for i in range(1,n+1): 
            self.append_texture(arcade.load_texture("Tiles/" + type(self).__name__ + str(TILE_SIZE) + "-" + str(i) + ".png"))
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
    def can_be_penetrated(self, by: "Element") -> bool: return isinstance(by, Miner)

class Wall(Element):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class MetalWall(Wall):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)
    def can_break(self) -> bool:  return False

class Ore(Element):
    def __init__(self, game: Game, x: int, y: int, n:int = 0) -> None: super().__init__(game, x, y, n)

    def tick(self) -> None:
        if self.try_move(0, -1): return
        ix = random.randint(0, 1) * 2 - 1;  # pick a side at random
        self.try_roll(ix) or self.try_roll(-ix)

    def try_roll(self, ix: int) -> bool:
        below = self.game.cave.at(self.x, self.y -1)
        return (isinstance(below, Ore) or isinstance(below, Wall)) and self.can_move(ix, -1) and self.try_move(ix, 0)

    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Miner) or isinstance(into, Enemy):
            self.game.cave.explode(self.x, self.y)

class Boulder(Ore):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y)

class Diamond(Ore):
    def __init__(self, game: Game, x: int, y: int) -> None: super().__init__(game, x, y, 3)
    def can_be_penetrated(self, by: Element) -> bool: return isinstance(by, Miner)
    def can_break(self) -> bool:  return False
    def on_destroy(self) -> None: self.game.cave.nb_diamonds -= 1
    def tick(self) -> None:
        shine = random.randint(1, 40)
        if shine > 3: shine = 0
        self.set_texture(shine)
        super().tick()

class Miner(Element):
    def __init__(self, game: Game, x: int, y: int, id: int) -> None:
        super().__init__(game, x, y)
        self.pushing = 0 ; self.score = 0;  self.speed *= 2
        self.controls = \
            (arcade.key.Z, arcade.key.Q,  arcade.key.S, arcade.key.D) if id == 1 \
            else (arcade.key.I, arcade.key.J,  arcade.key.K, arcade.key.L) if id == 2 \
            else (arcade.key.UP, arcade.key.LEFT, arcade.key.DOWN, arcade.key.RIGHT)

    def can_be_penetrated(self, by: Element) -> bool:
        return (isinstance(by, Ore) and by.moving) or isinstance(by, Enemy)

    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Diamond): self.score += 1
        self.pushing = 0

    def pressed(self, key: int) -> bool:
        return self.controls[key] in self.game.keys

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

    def on_destroy(self) -> None: pass # TODO : game over

class Explosion(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.wait = 1/8
    def can_be_penetrated(self, by: "Element") -> bool: return True
    def tick(self) -> None: self.game.cave.replace(self, None)

class Exit(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.append_texture(arcade.load_texture("Tiles/" + MetalWall.__name__ + str(TILE_SIZE) + "-0.png"))
        self.opened = False ; self.set_texture(1)

    def tick(self) -> None:
        if self.game.cave.nb_diamonds == 0:
            self.opened = True ; self.set_texture(0)

    def can_be_penetrated(self, by: "Element") -> bool: 
        return isinstance(by, Miner) and self.opened
    
    def on_destroy(self) -> None: self.game.cave.next_level()

class Enemy(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.dir = [-1,0]

    def can_be_penetrated(self, by: Element) -> bool:
        return isinstance(by, Ore)

    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Miner):
            self.game.cave.explode(self.x, self.y)

    def tick(self) -> None:
        if self.try_move(self.dir[1], -self.dir[0]):
            self.dir = [self.dir[1], -self.dir[0]]
        elif self.try_move(self.dir[0], self.dir[1]):
            self.dir = self.dir
        elif self.try_move(-self.dir[1], self.dir[0]):
            self.dir = [-self.dir[1], self.dir[0]]
        elif self.try_move(-self.dir[0], -self.dir[1]):
            self.dir = [-self.dir[0], -self.dir[1]]

    def on_destroy(self) -> None: self.game.cave.explode(self.x, self.y)