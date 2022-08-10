import arcade
import random
import time
import math
from typing import Optional, Union
from boulder_dash import Game, Cave, Player

class Sound(arcade.Sound):
    def __init__(self, file) -> None: 
        super().__init__(file)
        self.last_played = -math.inf
        super().play().delete() # force audio preloading
    def play(self):
        now = time.time()
        if (now - self.last_played < 1/60): return # already played within the same frame
        self.last_played = now
        return super().play()

class Sprite(arcade.Sprite):
    TILE_SIZE = 64 # choose from 16, 64
    TILE_SCALE = Game.TILE_SIZE / TILE_SIZE
    DEFAULT_SPEED = 10 # squares per second
    PRIORITY_HIGH = 0
    PRIORITY_MEDIUM = 1
    PRIORITY_LOW = 2

    def __init__(self, cave: Cave, x: int, y: int, n: int = 1) -> None:
        super().__init__(None, Sprite.TILE_SCALE)
        self.nb_skins = 0
        for i in range(0, n): self.add_skin(type(self).__name__, i)
        if n > 0: self.set_skin(0)
        self.cave = cave
        self.x = x ; self.y = y ; self.dir = (0, 0)
        self.wait = 0 ; self.speed = Sprite.DEFAULT_SPEED
        self.moved = self.moving = False ; self.priority = Sprite.PRIORITY_MEDIUM
        self.compute_pos()

    def add_skin(self, name: str, id: int, flip_h: bool = False, flip_v: bool = False) -> None: 
        texture = arcade.load_texture(f'res/{name}{Sprite.TILE_SIZE}-{id}.png', 0,0, Sprite.TILE_SIZE, Sprite.TILE_SIZE, flip_h, flip_v)
        self.append_texture(texture)
        self.nb_skins += 1
    def set_skin(self, i: int) -> None: self.skin = i; self.set_texture(i)
    def next_skin(self) -> None: self.set_skin( (self.skin+1) % self.nb_skins )

    def compute_pos(self) -> None:
        self.center_x = Sprite.TILE_SIZE * Sprite.TILE_SCALE * (self.x + 0.5)
        self.center_y = Sprite.TILE_SIZE * Sprite.TILE_SCALE * (self.y + 0.5)

    def neighbor(self, ix:int, iy:int) -> Optional['Sprite'] :
        return self.cave.at(self.x + ix, self.y + iy)

    def is_kind_of(self, cond: Optional[Union[int, type]]):
        return cond is None or (isinstance(cond, type) and isinstance(self, cond)) or self.priority == cond

    def can_move(self, ix: int, iy: int)  -> bool:
        return self.cave.can_move(self, ix, iy)

    def try_move(self, ix: int, iy: int) -> bool:
        self.dir = (ix, iy)
        if self.cave.try_move(self, ix, iy):
            self.compute_pos()
            self.moved = True
            return self.try_wait()
        return False

    def try_wait(self) -> bool:
        self.wait = 1 / self.speed
        return True

    def on_update(self, delta_time) -> None:
        if self.wait > 0: 
            self.wait -= delta_time
        else: 
            self.moved = False
            self.tick() 
            self.moving = self.moved

    def tick(self): pass
    def can_be_occupied(self, by: 'Sprite', ix:int, iy:int) -> bool: return False
    def on_moved(self, into: Optional['Sprite']) -> None: pass
    def can_break(self) -> bool:  return True
    def on_destroy(self) -> None: pass

class Unknown(Sprite):
    def __init__(cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y)

class Soil(Sprite):
    sound = Sound(":resources:sounds/rockHit2.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y)
    def can_be_occupied(self, by: Sprite, ix:int, iy:int) -> bool: return isinstance(by, Miner)
    def collect(self) -> int : Soil.sound.play() ; return 0

class Wall(Sprite):
    def __init__(self, cave: Cave, x: int, y: int, n: int = 1) -> None: super().__init__(cave, x, y, n)

class BrickWall(Wall):
    def __init__(self, cave: Cave, x: int, y: int, n: int = 1) -> None: super().__init__(cave, x, y, n)

class MetalWall(Wall):
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y)
    def can_break(self) -> bool:  return False

class ExpandingWall(Wall):
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 2)
        self.add_skin(ExpandingWall.__name__, 1, True)
        self.speed /= 2
        self.try_wait()

    def tick(self) -> None:
        self.set_skin(0)
        for ix in [-1,+1]:
            if self.neighbor(ix, 0) is None:
                tile = ExpandingWall(self.cave, self.x+ix, self.y)
                tile.set_skin(2 if ix == -1 else 1)
                self.cave.set(self.x + ix, self.y, tile)
                Boulder.sound_fall.play()
                self.try_wait()

class Pushable(Sprite):
    sound = Sound(":resources:sounds/hurt1.wav")
    def __init__(self, cave: Cave, x: int, y: int, n:int = 1) -> None: 
        super().__init__(cave, x, y, n)

class Massive(Pushable):
    sound_fall = Sound(":resources:sounds/hurt2.wav")

    def __init__(self, cave: Cave, x: int, y: int, n:int = 1) -> None: 
        super().__init__(cave, x, y, n)

    def can_move(self, ix: int, iy: int)  -> bool: 
        return iy <= 0 and super().can_move(ix, iy)
    
    def tick(self) -> None:
        if self.try_move(0, -1): return
        elif self.moving: self.on_end_fall(self.neighbor(0, -1))
        ix = random.randint(0, 1) * 2 - 1;  # pick a side at random
        self.try_roll(ix) or self.try_roll(-ix)
    
    def on_end_fall(self, onto: Sprite) -> None:
        type(self).sound_fall.play()
        if isinstance(onto, CrackedBoulder):
            onto.on_end_fall(None)
    
    def try_roll(self, ix: int) -> bool:
        below = self.neighbor(0, -1)
        return (isinstance(below, Massive) or isinstance(below, BrickWall)) and self.can_move(ix, -1) and self.try_move(ix, 0)

class Boulder(Massive):
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y)

class Diamond(Massive):
    sound = Sound(":resources:sounds/coin5.wav")
    sound_fall = Sound(":resources:sounds/coin4.wav")
    sound_explosion = Sound(":resources:sounds/secret4.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None:
       super().__init__(cave, x, y, 4)

    def can_be_occupied(self, by: Sprite, ix:int, iy:int) -> bool: return isinstance(by, Miner)
    def can_break(self) -> bool:  return False

    def collect(self) -> int: 
        Diamond.sound.play()
        self.cave.collected += 1
        return 5 if self.cave.is_complete() else 2

    def tick(self) -> None:
        if random.randint(0,2) == 1:
            shine = random.randint(1, 40)
            if shine > 3: shine = 0
            self.set_skin(shine)
        super().tick()

class CrackedBoulder(Boulder):
    WAIT_CRACK = .125 # sec
    def __init__(self, cave: Cave, x: int, y: int, crack_type = None) -> None: 
        super().__init__(cave, x, y)
        self.add_skin(type(self).__name__, 0, True)
        self.crack_time = math.inf
        self.crack_type = crack_type if crack_type is not None else Explosion
    def on_end_fall(self, onto: Sprite) -> None:
        super().on_end_fall(onto)
        self.next_skin()
        self.crack_time = time.time() + CrackedBoulder.WAIT_CRACK 

    def tick(self) -> None:
        if time.time() >= self.crack_time : self.cave.replace(self, self.crack_type)
        else: super().tick()

class Mineral(CrackedBoulder):
    sound_fall = Diamond.sound_fall
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y, Diamond)

class WoodCrate(Pushable):
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y)

class MetalCrate(Pushable):
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y)
    def can_break(self) -> bool:  return False

class Explosion(Sprite):
    WAIT_CLEAR = .125 # seconds
    sound_explosion = Sound(":resources:sounds/explosion2.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y)
        self.wait = Explosion.WAIT_CLEAR
    def can_be_occupied(self, by: Sprite, ix:int, iy:int) -> bool: return True
    def tick(self) -> None: self.cave.replace(self, None)

class Entry(Sprite):
    WAIT_OPEN = 0.75 # seconds
    sound = Sound(":resources:sounds/jump4.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 0)
        self.add_skin(Exit.__name__, 1)
        self.set_skin(0)
        self.wait = Entry.WAIT_OPEN
        self.player_assigned = False

    def assign_player(self) -> None:
        if self.cave.nb_players < len(self.cave.game.players):
            self.player = self.cave.game.players[self.cave.nb_players]
            self.cave.nb_players += 1
            self.player.center_on(self.center_x, self.center_y, 1)
        else: self.player = None
        self.player_assigned = True

    def on_update(self, delta_time) -> None:
        if not self.player_assigned: self.assign_player()
        super().on_update(delta_time)

    def tick(self) -> None:
        if self.player is not None and self.player.life > 0: 
            Entry.sound.play()
            self.cave.replace(self, self.cave.miner_type(self.cave, self.x, self.y, self.player)); 
        else:
            Explosion.sound_explosion.play()
            self.cave.replace(self, Explosion); 

class Exit(Sprite):
    sound = Sound(":resources:sounds/upgrade1.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 2)
        self.opened = False

    def tick(self) -> None:
        if not self.opened and self.cave.is_complete() :
            Entry.sound.play()
            self.opened = True ; self.set_skin(1)

    def can_be_occupied(self, by: Sprite, ix:int, iy:int) -> bool: 
        return isinstance(by, Miner) and self.opened
    def can_break(self) -> bool:  return False

    def on_destroy(self) -> None: 
        Exit.sound.play()
        self.cave.set_status(Cave.SUCCEEDED)

class Character(Sprite):
    def __init__(self, cave: Cave, x: int, y: int, n: int = 1) -> None:
       super().__init__(cave, x, y, n)

    def can_be_occupied(self, by: Sprite, ix:int, iy:int) -> bool: 
        return isinstance(by, Massive) and by.moving

    def on_destroy(self) -> None: self.cave.explode(self.x, self.y)

class Miner(Character):
    def __init__(self, cave: Cave, x: int, y: int, player: Player) -> None:
        super().__init__(cave, x, y, 2)
        self.set_skin(player.id % self.nb_skins)
        self.pushing = None
        self.player = player
        self.priority = Sprite.PRIORITY_HIGH

    def can_be_occupied(self, by: Sprite, ix:int, iy:int) -> bool:
        return ( 
            self.cave.status == Cave.IN_PROGRESS and
            (super().can_be_occupied(by, ix, iy) or isinstance(by, Firefly))
        )

    def on_moved(self, into: Optional[Sprite]) -> None:
        if isinstance(into, Diamond) or isinstance(into, Soil):
            self.player.score += into.collect()
        self.pushing = None

    def on_update(self, delta_time) -> None:
        super().on_update(delta_time)
        if self.moved: self.player.center_on(self.center_x, self.center_y)

    def tick(self) -> None:
        if self.cave.status != Cave.IN_PROGRESS: return
        for dir in [(-1,0),(+1,0),(0,-1),(0,+1)]:
            if self.player.is_direction(*dir):
                if self.try_move(*dir): return
        for dir in [(-1,0),(+1,0),(0,-1),(0,+1)]:
            if self.player.is_direction(*dir):
                if self.try_push(*dir): return

    def try_push(self, ix:int, iy:int) -> bool:
        pushed = self.neighbor(ix, iy)
        if isinstance(pushed, Portal): pushed = pushed.look_through(ix, iy)
        if isinstance(pushed, Pushable):
            if self.pushing == (ix, iy):
                if pushed.try_move(ix, iy): 
                    Pushable.sound.play()
                    return self.try_move(ix, iy)
            else:
                self.dir = (ix, iy)
                self.pushing = self.dir;
                self.try_wait()
        return False

    def on_destroy(self) -> None:
        super().on_destroy()
        self.player.kill()

class Girl(Miner):
    def __init__(self, cave: Cave, x: int, y: int, player: Player) -> None: super().__init__(cave, x, y, player)

class Firefly(Character):
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 2)
        self.speed /= 2 ; self.dir = (-1, 0)
        self.priority = Sprite.PRIORITY_LOW

    def can_be_occupied(self, by: Sprite, ix:int, iy:int) -> bool: 
        return isinstance(by, Massive) or isinstance(by, Miner)
    
    def on_moved(self, into: Optional[Sprite]) -> None:
        if isinstance(into, Amoeba): self.cave.replace(self, None)

    def try_wander(self) -> bool:
        (ix,iy) = self.dir
        # always go left
        return self.try_move(-iy, ix) or self.try_move(ix, iy) or self.try_move(iy, -ix) or self.try_move(-ix, -iy) or self.try_wait()
    
    def tick(self) -> None:
        self.next_skin()
        # if adjacent to a miner, try to catch him
        for look in [(-1,0),(+1,0),(0,-1),(0,+1)]:
            if isinstance(self.neighbor(*look), Miner) and self.try_move(*look): return
        # else wander around
        self.try_wander()

    def on_destroy(self) -> None: self.cave.explode(self.x, self.y)

class Butterfly(Firefly):
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y)
        self.dir = (0, -1)

    def try_wander(self) -> bool:
        (ix,iy) = self.dir
        # always go right
        return self.try_move(iy, -ix) or self.try_move(ix, iy) or self.try_move(-iy, ix) or self.try_move(-ix, -iy) or self.try_wait()

    def on_destroy(self) -> None: self.cave.explode(self.x, self.y, Diamond)

class MagicWall(BrickWall): 
    def __init__(self, cave: Cave, x: int, y: int) -> None:
       super().__init__(cave, x, y, 3)
       self.add_skin(BrickWall.__name__, 0)

    def tick(self) -> None:
        if random.randint(0, 6) == 0: self.set_skin(random.randint(0, self.nb_skins - 1))
        super().tick()

    def can_be_occupied(self, by: 'Sprite', ix:int, iy:int) -> bool:
        return isinstance(by, Massive) and by.moving

    def on_destroy(self) -> None:
        # won't be destroyed by falling ore, do its magic instead !
        ore = self.cave.at(self.x, self.y)
        if isinstance(ore, Massive): 
            ore = Boulder(self.cave, self.x, self.y) if isinstance(ore, Diamond) else Diamond(self.cave, self.x, self.y)
            ore.tick() # continue its fall through...
            self.cave.set(self.x, self.y, self)

class Amoeba(Sprite):
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y)
        self.add_skin(Amoeba.__name__, 0, True, False) ; self.add_skin(Amoeba.__name__, 0, False, True) ; self.add_skin(Amoeba.__name__, 0, True, True) 
        self.set_skin(random.randint(0, self.nb_skins - 1))
        self.try_wait()
        self.trapped = False

    def tick(self) -> None:
        if random.randint(0, 4) == 0: self.set_skin(random.randint(0, self.nb_skins - 1))
        self.trapped = True
        for look in [(-1,0),(+1,0),(0,-1),(0,+1)]:
            neighbor = self.neighbor(*look)
            if neighbor is None or isinstance(neighbor, Soil):
                self.trapped = False
                proba = 20 if neighbor is None else 80
                if random.randint(0, proba) == 0:
                    (ix,iy) = look ; (x,y) = (self.x+ix, self.y+iy)
                    self.cave.set(x, y, Amoeba(self.cave, x, y))
        self.try_wait()

    def can_be_occupied(self, by: 'Sprite', ix:int, iy:int) -> bool: return isinstance(by, Firefly)

    @staticmethod
    def on_update_cave(cave: Cave) -> bool:
        count = 0 ; trapped = True
        for amoeba in cave.sprites(Amoeba): 
            count += 1
            if not amoeba.trapped: trapped = False
        if trapped and count > 0:
            cave.replace_all(Amoeba, Diamond)
            Diamond.sound_explosion.play()
        elif count >= 200:
            cave.replace_all(Amoeba, Boulder)
            Boulder.sound_fall.play()

class Portal(Sprite):
    sound = Sound(":resources:sounds/phaseJump1.wav")
    next_link = None
    def __init__(self, cave: Cave, x: int, y: int) -> None:
       super().__init__(cave, x, y, 2)
       if Portal.next_link is None:
          Portal.next_link = self
          self.link = None
       else:
         self.set_skin(1)
         self.link = Portal.next_link
         Portal.next_link.link = self
         Portal.next_link = None

    def can_break(self) -> bool:  return False

    def look_through(self, ix:int, iy:int) -> Optional[Sprite]:
        return self.cave.at(self.link.x + ix, self.link.y + iy)

    def can_be_occupied(self, by: 'Sprite', ix:int, iy:int) -> bool: 
        (x,y) = (by.x, by.y)
        (by.x, by.y) = (self.link.x, self.link.y)
        teleport = by.can_move(ix, iy)
        (by.x, by.y) = (x,y)
        return teleport

    def on_destroy(self) -> None:
        # won't be destroyed by entering object, do its magic instead !
        Portal.sound.play()
        entering = self.cave.at(self.x, self.y) 
        self.cave.set(self.x, self.y, self)
        (entering.x, entering.y) = (self.link.x, self.link.y)
        if not entering.try_move(*entering.dir):
            if isinstance(entering, Miner): entering.try_push(*entering.dir)
        self.cave.set(self.link.x, self.link.y, self.link)
