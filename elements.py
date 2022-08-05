import arcade
import random
from typing import Optional
from boulder_dash import *

TILE_SIZE = 64
TILE_SCALE = 0.75
MAX_SPEED = 8 # squares per second

class Element(arcade.Sprite):
    def __init__(self, game: "Game", x: int, y: int) -> None:
        super().__init__("Tiles/" + type(self).__name__ + str(TILE_SIZE) + "-0.png", TILE_SCALE)
        self.game = game ;
        self.x = x ; self.y = y;
        self.center_x = TILE_SIZE * TILE_SCALE * (x + 0.5)
        self.center_y = TILE_SIZE * TILE_SCALE * (y + 0.5)
        self.wait = 0 ; self.moved = self.moving = False

    def try_move(self, ix: int, iy: int)  -> bool:
      if self.game.stage.try_move(self, self.x + ix, self.y + iy):
          self.center_x += TILE_SIZE * TILE_SCALE * ix
          self.center_y += TILE_SIZE * TILE_SCALE * iy
          self.wait = 1 / MAX_SPEED
          self.moved = True
          return True
      return False

    def on_update(self, delta_time) -> None:
        if self.wait > 0: self.wait -= delta_time
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

class Soil(Element):
    def __init__(self, game: "Game", x: int, y: int) -> None:
        super().__init__(game, x, y)

    def can_be_penetrated(self, by) -> bool:
        return isinstance(by, Miner)

class Wall(Element):
    def __init__(self, game: "Game", x: int, y: int) -> None:
        super().__init__(game, x, y)

class Rolling(Element):
    def __init__(self, game: "Game", x: int, y: int) -> None:
        super().__init__(game, x, y)

    def tick(self) -> None:
        if self.try_move(0, -1): return
        ix = random.randint(0, 1) * 2 - 1;  # pick a side at random
        self.try_roll(ix) or self.try_roll(-ix)

    def try_roll(self, ix: int) -> bool:
        below = self.game.stage.at(self.x, self.y -1)
        if not isinstance(below, Rolling): return False
        if not self.game.stage.at(self.x + ix, self.y) is None : return False
        return self.try_move(ix, -1);

class Boulder(Rolling):
    def __init__(self, game: "Game", x: int, y: int) -> None:
        super().__init__(game, x, y)
        
    def on_moved(self, into: Optional["Element"]) -> None:
        if isinstance(into, Miner):
            pass # TODO : explode, game over

class Diamond(Rolling):
    def __init__(self, game: "Game", x: int, y: int) -> None:
        super().__init__(game, x, y)

    def can_be_penetrated(self, by: "Element") -> bool:
        return isinstance(by, Miner)

    def on_moved(self, into: Optional["Element"]) -> None:
        if isinstance(into, Miner): 
            self.game.stage.replace(self, into)
            into.score += 1

class Miner(Element):
    def __init__(self, game: "Game", x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.score = 0

    def can_be_penetrated(self, by: "Element") -> bool:
        return isinstance(by, Rolling) and by.moving

    def on_moved(self, into: Optional["Element"]) -> None:
        if isinstance(into, Diamond): self.score += 1

    def tick(self) -> None:
        if   arcade.key.LEFT  in self.game.keys:  
            if not self.try_move(-1, 0): self.try_push(-1)
        elif arcade.key.RIGHT in self.game.keys:  
            if not self.try_move(+1, 0): self.try_push(+1)
        elif arcade.key.UP    in self.game.keys:
            self.try_move(0, +1)
        elif arcade.key.DOWN  in self.game.keys:
            self.try_move(0, -1)
    
    def try_push(self, ix: int) -> bool:
        return False # TODO
