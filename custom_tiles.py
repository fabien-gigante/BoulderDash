from typing import Optional, Tuple
import math
from game import Cave, Player, Sound
from tiles import *

class BackTile(Tile):
    ''' A static background tile. Lies on the floor, below normal plates. '''
    def can_break(self) -> bool:  return False
    def on_loaded(self) -> None:
        self.cave.replace(self, None)
        self.cave.set(self.x, self.y, self, True)

class SmallDiamond(Tile, ICollectable):
    ''' A small and light diamond. Not subject to gravity. Worth lower value. '''
    def can_be_occupied(self, by: Tile, _ix: int, _iy: int) -> bool: return isinstance(by, Miner)
    def collect(self) -> int:
        Diamond.sound.play()
        if (self.x+self.y) % 2 == 0: self.cave.collected += 1
        return 1

class Energizer(Diamond):
    ''' A special diamond that frightens insects for some time. A frightened insect can be killed. '''
    TIME_OUT = 5
    def collect(self) -> int:
        Player.sound.play()
        for insect in self.cave.tiles(Insect): 
            insect.frightened = Energizer.TIME_OUT
            (ix,iy) = insect.dir ; insect.dir = (-ix,-iy)
        return super().collect()

class Balloon(Weighted, IRounded):
    ''' A balloon tile lighter than air. Falls upwards. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
       super().__init__(cave, x, y)
       self.gravity = +1

class CrackedBoulder(Boulder, IFragile):
    ''' A fragile boulder. Breaks when falling or being hit. '''
    WAIT_CRACK = .125 # sec
    def __init__(self, cave: Cave, x: int, y: int, crack_type = None) -> None: 
        super().__init__(cave, x, y)
        self.add_skin(type(self).__name__, 0, True)
        self.crack_time = math.inf
        self.crack_type = crack_type if crack_type is not None else Explosion

    def crack(self, by:Tile) -> None:
        super().crack(by)
        self.next_skin()
        self.crack_time = CrackedBoulder.WAIT_CRACK 

    def end_fall(self, onto: Tile) -> None:
        super().end_fall(onto)
        self.crack(onto)

    def on_update(self, delta_time: float = 1/60) -> None:
        self.crack_time -= delta_time
        super().on_update(delta_time)

    def tick(self) -> None:
        if self.crack_time <= 0 : self.cave.replace(self, self.crack_type)
        else: super().tick()

class Mineral(CrackedBoulder):
    ''' A cracked fragile boulder. Turns into a diamond when it breaks. '''
    sound_fall = Diamond.sound_fall
    def __init__(self, cave: Cave, x: int, y: int) -> None: super().__init__(cave, x, y, Diamond)

class Girl(Miner):
    ''' A female miner with a different skin... '''

class Portal(Tile):
    ''' A gate tile that allows teleporting. Works in pairs. Objects can fall or be pushed through portals. Unbreakable. '''
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
    def position(self, observer: Optional['Tile'], ix: int, iy: int) -> Tuple[int,int]:
        return self.link.offset(ix, iy)

class Crate(Pushable):
    ''' A pushable tile. Not subject to gravity. Turns into diamond when all crate targets have crates on them. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 2)
        self.solved = False
    def on_moved(self, into: Optional[Tile]) -> None:
        placed = isinstance(self.cave.at(self.x, self.y, True), CrateTarget)
        self.set_skin(1 if placed else 0)
        super().on_moved(into)

    @staticmethod
    def on_global_update(cave: Cave) -> bool:
        targets = [*cave.tiles(CrateTarget, True)]
        if len(targets) > 0 and all(isinstance(target.neighbor(0, 0), Crate) for target in targets):
            for crate in (target.neighbor(0, 0) for target in targets):
                crate.solved = True
                cave.replace(crate, Diamond)
            Diamond.sound_explosion.play()

Tile.global_updates.append(Crate.on_global_update)

class WoodCrate(Crate):
    ''' A fragile wodden crate. Explodes when hit. '''
    def can_be_occupied(self, by: Tile, _ix: int, _iy: int) -> bool: 
        return isinstance(by, Massive) and by.moving
    def on_destroy(self) -> None:
        if not self.solved: self.cave.explode(self.x, self.y)

class MetalCrate(Crate):
    ''' A metal crate. Unbreakable. '''
    def can_break(self) -> bool:  return False

class CrateTarget(BackTile):
    ''' A background tile representing a target position for a crate. Crates must be placed on those tiles. '''
    def is_placed(self) -> bool:return isinstance(self.neighbor(0, 0), Crate)

class Door(MetalWall):
    ''' A door that can be opened when activated. '''
    def __init__(self, cave: Cave, x: int, y: int, n: int = 2) -> None:
        super().__init__(cave, x, y, n)
        self.opened = False
    def can_break(self) -> bool:  return False
    def toggle(self) -> None : 
        self.opened = not self.opened
        self.next_skin()
    def position(self, observer: Optional['Tile'], ix: int, iy: int) -> Tuple[int,int]:
        if self.opened and iy == 0: return self.offset(ix, iy)
        return super().position(observer, ix, iy)

class ActivableDoor(Door, IActivable):
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 0)
        self.add_skin(Door.__name__, 0);
        self.add_skin(Door.__name__, 1);
    def try_activate(self, by: Tile, ix:int, iy:int) -> bool : 
        self.toggle()
        return True

class LockedDoor(Door):
    ''' A locked door that unlocks only when the corresponding key is collected. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 0)
        self.id = len([*self.cave.tiles(LockedDoor)]) % 3
        self.add_skin(type(self).__name__, self.id);
    def unlock(self, key: 'Key') -> None :
        if self.id == key.id: 
            Exit.sound.play()
            self.cave.replace(self, ActivableDoor)

class Key(Tile, ICollectable):
    ''' A collectable tile representing a key. Unlocks corresponding locked doors. '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 0)
        self.id = len([*self.cave.tiles(Key)]) % 3
        self.add_skin(type(self).__name__, self.id);
    def can_be_occupied(self, by: Tile, _ix: int, _iy: int) -> bool: return isinstance(by, Miner)
    def collect(self) -> int :
        for door in self.cave.tiles(LockedDoor): door.unlock(self)
        return 0

class ITriggerable(Interface):
    def trigger(self, by: Tile) -> None: pass

class TriggeredDoor(Door, ITriggerable):
    ''' A closed door that can only be opened by a remote trigger (such as a switch) '''
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 0)
        self.id = len([*self.cave.tiles(TriggeredDoor)]) % 3
        self.add_skin(type(self).__name__, self.id);
        self.add_skin(Door.__name__, 1);
    def trigger(self, by: Tile) -> None : 
        if self.id == by.id: self.toggle()

class Lever(Tile, IActivable, IFragile):
    def __init__(self, cave: Cave, x: int, y: int) -> None:
        super().__init__(cave, x, y, 0)
        self.id = len([*self.cave.tiles(Lever)]) % 3
        self.add_skin(type(self).__name__, self.id);
        self.add_skin(type(self).__name__, self.id, True);
    def try_activate(self, by: Tile, ix:int, iy:int) -> bool : self.toggle(by) ; return True
    def crack(self, by: Tile) -> None: self.toggle(by)
    def toggle(self, by: Tile) -> None:
        self.next_skin()
        IFragile.sound.play()
        for door in self.cave.tiles(TriggeredDoor): door.trigger(self)

Tile.registered = {
   **Tile.registered, 
   'k': CrackedBoulder, 'n': Mineral,'c': WoodCrate, 'h': MetalCrate, '+': CrateTarget, 
   'l': Balloon, 'p': Portal, 'g': Energizer, '*': SmallDiamond,
   'D': ActivableDoor, 'L': LockedDoor, '%': Key, 'T': TriggeredDoor, '/': Lever }