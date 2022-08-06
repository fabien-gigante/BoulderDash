import arcade
import random
from typing import Optional
from boulder_dash import Game, Cave, Player
from collections import namedtuple

class Element(arcade.Sprite):
    TILE_SIZE = 16 # 64
    TILE_SCALE = Game.TILE_SIZE / TILE_SIZE
    DEFAULT_SPEED = 16 # squares per second

    def __init__(self, game: Game, x: int, y: int, n: int = 1) -> None:
        super().__init__(None, Element.TILE_SCALE)
        self.nb_skins = 0
        for i in range(0, n): self.add_skin(type(self).__name__, i)
        if n > 0: self.set_skin(0)
        self.game = game
        self.x = x ; self.y = y;
        self.wait = 0 ; self.speed = Element.DEFAULT_SPEED
        self.moved = self.moving = False
        self.compute_pos()

    def add_skin(self, name: str, id: int) -> None: 
        self.append_texture(arcade.load_texture('Tiles/' + name + str(Element.TILE_SIZE) + '-' + str(id) + '.png'))
        self.nb_skins += 1
    def set_skin(self, i: int) -> None: self.skin = i; self.set_texture(i)
    def next_skin(self) -> None: self.set_skin( (self.skin+1) % self.nb_skins )
     
    def compute_pos(self) -> None:
        self.center_x = Element.TILE_SIZE * Element.TILE_SCALE * (self.x + 0.5)
        self.center_y = Element.TILE_SIZE * Element.TILE_SCALE * (self.y + 0.5)

    def neighbor(self, ix:int, iy:int) -> Optional['Element'] :
        return self.game.cave.at(self.x + ix, self.y + iy)

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
        below = self.neighbor(0, -1)
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
        if random.randint(0,2) == 1:
            shine = random.randint(1, 40)
            if shine > 3: shine = 0
            self.set_skin(shine)
        super().tick()

class Explosion(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.wait = .125 # seconds
    def can_be_penetrated(self, by: Element) -> bool: return True
    def tick(self) -> None: self.game.cave.replace(self, None)

class Entry(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y, 0)
        self.add_skin(Exit.__name__, 1)
        self.set_skin(0)
        self.wait = 0.75 # seconds
        self.player = self.game.players[self.game.cave.nb_players]
        self.game.cave.nb_players += 1
        self.game.center_on(self.center_x, self.center_y)

    def tick(self) -> None:
        if self.player.life > 0: self.game.cave.replace(self, Miner(self.game, self.x, self.y, self.player)); 
        else: self.game.cave.replace(self, None)

class Exit(Element):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y, 2)
        self.opened = False

    def tick(self) -> None:
        if self.game.cave.is_complete() :
            self.opened = True ; self.set_skin(1)

    def can_be_penetrated(self, by: Element) -> bool: 
        return isinstance(by, Miner) and self.opened
    
    def on_destroy(self) -> None: self.game.cave.set_status(Cave.SUCCEEDED)

class Character(Element):
    def __init__(self, game: Game, x: int, y: int, n: int = 1) -> None:
       super().__init__(game, x, y, n)
       self.dir = (0, 0)

    def can_be_penetrated(self, by: Element) -> bool: return (isinstance(by, Ore) and by.moving)
    def on_destroy(self) -> None: self.game.cave.explode(self.x, self.y)

class Miner(Character):
    def __init__(self, game: Game, x: int, y: int, player: Player) -> None:
        super().__init__(game, x, y)
        self.pushing = None
        self.player = player

    def can_be_penetrated(self, by: Element) -> bool:
        return self.game.cave.status == Cave.IN_PROGRESS and \
            (super().can_be_penetrated(by) or isinstance(by, Firefly))

    def on_moved(self, into: Optional[Element]) -> None:
        if isinstance(into, Diamond):
            self.game.cave.collected += 1 ; self.player.score += 1
        self.pushing = None

    def tick(self) -> None:
        if self.game.cave.status == Cave.IN_PROGRESS:
            self.dir = self.player.get_direction()
            if self.dir == (0,0): return
            if not self.try_move(*self.dir): self.try_push()
        self.player.center_on(self.center_x, self.center_y)
    
    def try_push(self) -> bool:
        if self.dir == (-1,0) or self.dir == (+1,0):
            pushed = self.neighbor(*self.dir)
            if isinstance(pushed, Boulder):
                if self.pushing == self.dir:
                    if pushed.try_move(*self.dir): return self.try_move(*self.dir)
                else: self.pushing = self.dir; self.wait = 1 / self.speed
        return False

    def on_destroy(self) -> None:
        super().on_destroy()
        self.player.kill()

class Firefly(Character):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y, 2)
        self.speed /= 2 ; self.dir = (-1, 0)

    def can_be_penetrated(self, by: Element) -> bool:
        return super().can_be_penetrated(by) or isinstance(by, Miner)

    def tick(self) -> None:
        self.next_skin()
        (ix,iy) = self.dir
        # if adjacent to a miner, self-destruct
        if isinstance(self.neighbor(-1,0), Miner) or isinstance(self.neighbor(+1,0), Miner) or \
           isinstance(self.neighbor(0,-1), Miner) or isinstance(self.neighbor(0,+1), Miner):
              self.game.cave.replace(self, None)
        # else follow the right wall...
        elif self.try_move(iy, -ix):  self.dir = (iy, -ix)
        elif self.try_move(ix, iy):   pass # go straight
        elif self.try_move(-iy, ix):  self.dir = (-iy, ix)
        elif self.try_move(-ix, -iy): self.dir = (-ix, -iy)

class Butterfly(Firefly):
    def __init__(self, game: Game, x: int, y: int) -> None:
        super().__init__(game, x, y)
        self.game.cave.to_kill += 1

    def on_destroy(self) -> None: 
        self.game.cave.explode(self.x, self.y, Diamond)
        self.game.cave.to_kill -= 1