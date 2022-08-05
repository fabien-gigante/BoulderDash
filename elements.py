import arcade
import random
from typing import Optional
from boulder_dash import Game

TILE_SIZE = 64
TILE_SCALE = 0.5
MAX_SPEED = 16 # squares per second
KEY_UP = 0
KEY_LEFT = 1
KEY_DOWN = 2
KEY_RIGHT = 3

class Element(arcade.Sprite):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__("Tiles/" + type(self).__name__ + str(TILE_SIZE) + "-0.png", TILE_SCALE)
        self.game = game ;
        self.x = x ; self.y = y;
        self.wait = 0 ; self.moved = self.moving = False
        self.compute_pos()
    
    def compute_pos(self) -> None:
        self.center_x = TILE_SIZE * TILE_SCALE * (self.x + 0.5)
        self.center_y = TILE_SIZE * TILE_SCALE * (self.y + 0.5)

    def can_move(self, ix: int, iy: int)  -> bool:
        return self.game.Cave.can_move(self, self.x + ix, self.y + iy)

    def try_move(self, ix: int, iy: int)  -> bool:
        if self.game.Cave.try_move(self, self.x + ix, self.y + iy):
            self.compute_pos()
            self.wait = 1 / MAX_SPEED
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

    def tick(self):
        pass

    def can_be_penetrated(self, by: "Element") -> bool:
        return False

    def on_moved(self, into: Optional["Element"]) -> None:
        pass

class Unknown(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)

class Soil(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)

    def can_be_penetrated(self, by: "Element") -> bool:
        return isinstance(by, Miner)

class Wall(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)

class Ore(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)

    def tick(self) -> None:
        if self.try_move(0, -1): return
        ix = random.randint(0, 1) * 2 - 1;  # pick a side at random
        self.try_roll(ix) or self.try_roll(-ix)

    def try_roll(self, ix: int) -> bool:
        below = self.game.Cave.at(self.x, self.y -1)
        return isinstance(below, Ore) and self.can_move(ix, -1) and self.try_move(ix, 0)

class Boulder(Ore):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        
    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Miner):
            pass # TODO : explode, game over

class Diamond(Ore):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)

    def can_be_penetrated(self, by: Element) -> bool:
        return isinstance(by, Miner)

    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Miner): 
            self.game.Cave.replace(self, into)
            into.on_moved(self)

class Miner(Element):
    def __init__(self, game: Game, x: int, y: int, id: int) -> None:
        super().__init__(game, x, y)
        self.score = 0
        self.controls = \
            (arcade.key.Z, arcade.key.Q,  arcade.key.S, arcade.key.D) if id == 1 \
            else (arcade.key.UP, arcade.key.LEFT, arcade.key.DOWN, arcade.key.RIGHT)

    def can_be_penetrated(self, by: Element) -> bool:
        return isinstance(by, Ore) and by.moving

    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Diamond): self.score += 1

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
        pushed = self.game.Cave.at(self.x + ix, self.y)
        if not isinstance(pushed, Boulder): return False
        if pushed.try_move(ix, 0): return self.try_move(ix, 0)
        return False
