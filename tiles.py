''' Standard tiles. '''

from typing import Optional
import math, random
from game import Cave, Player, Sound, Tile, Interface

class ICollectable(Interface):
    ''' Interface. Something that can be collected. '''
    def collect(self) -> int : return 0

class Soil(Tile, ICollectable):
    ''' A soil or dirt tile that miners can dig through. '''
    sound = Sound(":resources:sounds/rockHit2.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y)
    def can_be_occupied(self, by: Tile, _ix: int, _iy: int) -> bool: return isinstance(by, Miner)
    def collect(self) -> int : Soil.sound.play() ; return super().collect()

class IRounded(Interface):
    ''' Interface. Something on top of which things can roll. '''

class Wall(Tile):
    ''' An abstract wall tile. Blocks movement but breakable by explosions. '''

class BrickWall(Wall, IRounded):
    ''' A brick wall tile. '''

class MetalWall(Wall):
    ''' A metal wall tile. Unbreakable. '''
    def can_break(self) -> bool:  return False

class ExpandingWall(Wall):
    ''' An expanding brick wall that "grows" sideways whenever possible. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 2)
        self.add_skin(ExpandingWall, 1, True)
        self.horizontal = True ; self.speed /= 2
        self.try_wait()

    def tick(self) -> None:
        self.set_skin(0)
        for (ix, iy) in ([(-1,0), (+1,0)] if self.horizontal else [(0,-1), (0,+1)]):
            if self.can_move(ix, iy):
                tile = ExpandingWall(self.cave, self.x, self.y)
                tile.set_skin(2 if ix < 0 or iy < 0 else 1)
                Boulder.sound_fall.play()
                tile.try_move(ix, iy)

class IActivable(Interface):
    ''' Interface. Something that may ba activated or used. '''
    def try_activate(self, _by: Tile, _ix: int, _iy: int) -> bool : return False

class Pushable(Tile, IActivable):
    ''' An abstract tile that can be pushed by miners. '''
    sound = Sound(":resources:sounds/hurt1.wav")
    def try_activate(self, _by: Tile, ix:int, iy:int) -> bool :
        if self.try_move(ix, iy): Pushable.sound.play() ; return True
        return False

class IFragile(Interface):
    ''' Interface. Something that may crack (on react in some other way) when fallen upon. '''
    sound = Sound(":resources:sounds/hit4.wav")
    def crack(self, _by: Tile) -> None: IFragile.sound.play()

class Weighted(Pushable):
    ''' An abstract tile subject to gravity. It falls down and rolls off rounded objects. '''
    def __init__(self, cave: Cave, x: int, y: int, n: int = 1) -> None:
        super().__init__(cave, x, y, n)
        self.gravity = -1

    def can_move(self, ix: int, iy: int)  -> bool:
        return (self.gravity == 0 or iy == 0 or iy == self.gravity) and super().can_move(ix, iy)

    def tick(self) -> None:
        if self.gravity == 0 : return
        if self.try_move(0, self.gravity): return
        if self.moving: self.end_fall(self.neighbor(0, self.gravity))
        ix = random.choice([-1, +1])
        _ = self.try_roll(ix) or self.try_roll(-ix)

    def end_fall(self, onto: Tile) -> None: pass

    def try_roll(self, ix: int) -> bool:
        below = self.neighbor(0, self.gravity)
        if isinstance(below, IRounded) and self.can_move(ix, 0):
            # pretend we already moved (doors, portals don't like diagonal moves)
            (x,y) = (self.x, self.y)
            (self.x, self.y) = self.offset(ix, 0) 
            would_fall = self.can_move(0, self.gravity)
            (self.x, self.y) = (x,y)
            return would_fall and self.try_move(ix, 0)
        return False

class Massive(Weighted, IRounded):
    ''' A tile so massive it can crush creatures. '''
    sound_fall = Sound(":resources:sounds/hurt2.wav")

    def end_fall(self, onto: Tile) -> None:
        super().end_fall(onto)
        type(self).sound_fall.play()
        if isinstance(onto, IFragile): onto.crack(self)

class IMutable(Interface):
    ''' Interface. Can be transformed into something else. '''
    def mutate(self) -> Tile: return self

class Boulder(Massive, IMutable):
    ''' A rock or boulder tile. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y)
    def mutate(self) -> Tile: return Diamond(self.cave, self.x, self.y)

class Diamond(Massive, ICollectable, IMutable):
    ''' A diamond tile. Unbreakable. Animated. The goal of the game is to collect them. '''
    sound = Sound(":resources:sounds/coin5.wav")
    sound_fall = Sound(":resources:sounds/coin4.wav")
    sound_explosion = Sound(":resources:sounds/secret4.wav")

    def __init__(self, cave: Cave, x: int, y: int, n: int = 4) -> None:
        super().__init__(cave, x, y, n)
    def mutate(self) -> Tile: return Boulder(self.cave, self.x, self.y)

    def can_be_occupied(self, by: Tile, _ix: int, _iy: int) -> bool: return isinstance(by, Miner)
    def can_break(self) -> bool:  return False

    def collect(self) -> int:
        Diamond.sound.play()
        self.cave.collected += 1
        return 5 if self.cave.is_complete() else 2

    def tick(self) -> None:
        if random.randint(0,3) == 1:
            shine = random.randint(1, 10*self.nb_skins)
            if shine >= self.nb_skins: shine = 0
            self.set_skin(shine)
        super().tick()

class Explosion(Tile):
    ''' An explosition tile. Instant visual effect only, essentially behaves as an empty tile. '''
    WAIT_CLEAR = .25 # seconds
    sound_explosion = Sound(":resources:sounds/explosion2.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 4)
        self.wait = Explosion.WAIT_CLEAR
    def can_be_occupied(self, _by: Tile, _ix: int, _iy: int) -> bool: return True
    def on_update(self, delta_time: float = 1/60) -> None:
        super().on_update(delta_time)
        if self.wait > 0:
            self.set_skin( math.floor(self.nb_skins * (1 - self.wait/Explosion.WAIT_CLEAR)))
    def tick(self) -> None: self.cave.replace(self, None)

class Entry(Tile):
    ''' A door by which miners are entering the cave. '''
    WAIT_OPEN = 0.75 # seconds
    sound = Sound(":resources:sounds/jump4.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 0)
        self.add_skin(Exit, 1)
        self.wait = Entry.WAIT_OPEN
        self.once = False

    def on_update(self, delta_time: float = 1/60) -> None:
        if not self.once: self.focus() ; self.once = True
        super().on_update(delta_time)

    def can_be_occupied(self, by: Tile, _ix: int, _iy: int) -> bool: return isinstance(by, Miner)

    def tick(self) -> None:
        for player in self.cave.game.players:
            if player.life > 0:
                miner = self.cave.miner_type(self.cave, self.x, self.y, player)
                for direction in [(0,0),(-1,0),(+1,0),(0,+1),(0,-1),(-1,+1),(+1,+1),(-1,-1),(+1,-1)]:
                    if miner.try_move(*direction):
                        Entry.sound.play()
                        self.cave.set_status(Cave.IN_PROGRESS)
                        break
        if self.neighbor(0,0) is self:
            IFragile.sound.play()
            self.cave.replace(self, Explosion)
        self.cave.replace_all(Entry, Explosion)

class Exit(Tile):
    ''' A door that miners must use the exit the cave when completed. '''
    sound = Sound(":resources:sounds/upgrade1.wav")
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 2)
        self.opened = False

    def tick(self) -> None:
        if not self.opened and self.cave.is_complete() :
            Entry.sound.play()
            self.opened = True ; self.set_skin(1)

    def can_be_occupied(self, by: Tile, _ix: int, _iy: int) -> bool:
        return isinstance(by, Miner) and self.opened
    def can_break(self) -> bool:  return False

    def on_destroy(self) -> None:
        Exit.sound.play()
        self.cave.set_status(Cave.SUCCEEDED)

class Creature(Tile):
    ''' A creature in the cave, either miner or insect. Crushed by falling massive tiles. Explodes when dying. '''
    def can_be_occupied(self, by: Tile, _ix: int, _iy: int) -> bool:
        return isinstance(by, Massive) and by.moving

    def on_destroy(self) -> None: self.cave.explode(self.x, self.y, Explosion)

class Miner(Creature):
    ''' Main protagonist in the cave. Controled by a player. Can use tiles. '''
    CAMERA_SPEED = 0.02

    def __init__(self, cave: Cave, x: int, y: int, player: Player) -> None:
        super().__init__(cave, x, y, 4)
        self.set_skin(player.num % self.nb_skins)
        self.player = player
        self.priority = Tile.PRIORITY_HIGH

    def can_be_occupied(self, by: Tile, ix:int, iy:int) -> bool:
        if self.cave.status != Cave.IN_PROGRESS: return False
        return super().can_be_occupied(by, ix, iy) or (isinstance(by, Insect) and by.frightened == 0)

    def on_moved(self, into: Optional[Tile]) -> None:
        if isinstance(into, ICollectable): self.player.score += into.collect()

    def focus(self, speed = CAMERA_SPEED) -> None: super().focus(speed)
    def on_update(self, delta_time: float = 1/60) -> None:
        super().on_update(delta_time)
        if self.moved: self.focus()

    def try_move(self, ix: int, iy: int, allow_use = True) -> bool:
        return super().try_move(ix, iy) or (allow_use and self.try_use(ix, iy))

    def tick(self) -> None:
        if self.cave.status != Cave.IN_PROGRESS: return
        for direction in self.player.list_directions():
            if self.try_move(*direction, False): return
        for direction in self.player.list_directions():
            if self.try_use(*direction): return

    def try_use(self, ix:int, iy:int) -> bool:
        used = self.neighbor(ix, iy)
        if not isinstance(used, IActivable): return False
        if self.moving: return self.try_wait()
        return used.try_activate(self, ix, iy) and (self.try_move(ix, iy, False) or self.try_wait())

    def on_destroy(self) -> None:
        super().on_destroy()
        self.player.kill()

class Insect(Creature, ICollectable):
    ''' An abstract unfriendly creature in the cave. Wanders around. Kills miners. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 4)
        self.speed /= 2
        self.priority = Tile.PRIORITY_LOW
        self.frightened = 0
        self.rotation = 0

    def can_be_occupied(self, by: Tile, ix: int, iy: int) -> bool:
        return super().can_be_occupied(by, ix, iy) or isinstance(by, Miner)

    def try_wander(self) -> bool:
        (ix,iy) = self.dir
        if self.rotation > 0:
            return self.try_move(iy, -ix) or self.try_move(ix, iy) or self.try_move(-iy, ix) or self.try_move(-ix, -iy) or self.try_wait()
        if self.rotation < 0:
            return self.try_move(-iy, ix) or self.try_move(ix, iy) or self.try_move(iy, -ix) or self.try_move(-ix, -iy) or self.try_wait()
        return False

    def collect(self) -> int :
        Diamond.sound_explosion.play()
        return 5 if self.frightened > 0 else 0

    def on_update(self, delta_time: float = 1/60) -> None:
        super().on_update(delta_time)
        self.frightened = max(0, self.frightened - delta_time)

    def tick(self) -> None:
        skin = self.skin ^ 1
        if self.frightened == 0: skin &= 1
        elif self.frightened > 1: skin |= 2
        else: skin ^= 2
        self.set_skin( skin )
        # if adjacent to a miner, try to catch him
        if  self.frightened == 0:
            for look in [(-1,0),(+1,0),(0,-1),(0,+1)]:
                if isinstance(self.neighbor(*look), Miner) and self.try_move(*look): return
        # else wander around
        self.try_wander()

    def on_destroy(self) -> None:
        if self.frightened == 0 or not isinstance(self.neighbor(0,0), Miner):
            super().on_destroy()

class Firefly(Insect):
    ''' Simplest kind of insect. Wanders clockwise. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y)
        self.dir = (-1, 0) ; self.rotation = -1

class Butterfly(Insect):
    ''' An insect that explodes in diamonds. Wanders counter-clockwise. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y)
        self.dir = (0, -1) ; self.rotation = +1

    def on_destroy(self) -> None:
        if self.frightened == 0 or not isinstance(self.neighbor(0,0), Miner):
            self.cave.explode(self.x, self.y, Diamond)

class MagicWall(BrickWall):
    ''' An enchanted brick wall. A boulder or diamond that hits the wall gets changed into a diamond or boulder respectively, and falls through. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 3)
        self.add_skin(BrickWall, 0)

    def tick(self) -> None:
        if random.randint(0, 6) == 0: self.set_skin(random.randint(0, self.nb_skins - 1))
        super().tick()

    def can_be_occupied(self, by: 'Tile', _ix: int, iy: int) -> bool:
        return isinstance(by, Weighted) and by.moving

    def on_destroy(self) -> None:
        # won't be destroyed by falling rocks, do its magic instead !
        rock = self.neighbor(0, 0)
        if isinstance(rock, Weighted):
            (_,iy) = rock.dir
            if isinstance(rock, IMutable) and iy != 0:
                rock = rock.mutate() ; rock.moving = True
            rock.tick() # continue its fall through...
            self.cave.set(self.x, self.y, self)

class Amoeba(Tile):
    '''  Blob that grows randomly. If it can't, it turns into diamonds. If too large, it turns into boulders. Kills insects. '''
    DEATH_SIZE = 200
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y)
        self.add_skin(Amoeba, 0, True, False) ; self.add_skin(Amoeba, 0, False, True) ; self.add_skin(Amoeba, 0, True, True)
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

    def can_be_occupied(self, by: Tile, _ix:int, _iy:int) -> bool: return isinstance(by, Insect)

    def on_destroy(self) -> None:
        insect = self.neighbor(0, 0)
        if isinstance(insect, Insect): self.cave.replace(insect, Amoeba)

    @staticmethod
    def on_global_update(cave: Cave) -> bool:
        amoebas = [*cave.tiles(Amoeba)]
        if len(amoebas) > 0 and all(amoeba.trapped for amoeba in amoebas):
            cave.replace_all(Amoeba, Diamond)
            Diamond.sound_explosion.play()
        elif len(amoebas) >= Amoeba.DEATH_SIZE:
            cave.replace_all(Amoeba, Boulder)
            Boulder.sound_fall.play()

# Registrations
def register(registry):
    registry.global_updates.append(Amoeba.on_global_update)
    registry.registered_tiles = {
        **registry.registered_tiles,
        '♂': Miner, '.': Soil, 'w': BrickWall, 'W': MetalWall, 'r': Boulder, 'd': Diamond, 'E': Entry, 'X': Exit,
        'f': Firefly, 'b': Butterfly, 'a': Amoeba, 'm': MagicWall, 'e': ExpandingWall }
