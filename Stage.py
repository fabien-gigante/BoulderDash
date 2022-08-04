import arcade
import random
from Element import *

STAGE_HEIGHT = 12
STAGE_WIDTH = 16

class Stage:
    def __init__(self, game, file: str):
        self.game = game
        self.tiles = []
        for i in range(0,STAGE_HEIGHT):
            self.tiles.append([])
            for j in range(0,STAGE_WIDTH):
                tile = None
                dice = random.randint(0,3) 
                if dice == 1: tile = Soil(game, j, i)
                elif dice == 2: tile = Wall(game, j, i)
                self.tiles[i].append(tile)

        self.start_x = 5 ; self.start_y = 5
        self.tiles[self.start_y][self.start_x] = None

    def move(self, element, x, y):
        if x < 0 or y < 0 or x >= STAGE_WIDTH or y >= STAGE_HEIGHT:
            return False
        tile = self.tiles[y][x]
        if tile == None or tile.can_enter(element):
            self.tiles[element.y][element.x] = None
            self.tiles[y][x] = element
            element.x = x ; element.y = y
            return True
        else:
            return False

    def draw(self):
        for row in self.tiles:
            for tile in row:
                if tile != None: tile.draw()

    def on_update(self, delta_time):
        for row in self.tiles:
            for tile in row:
                if tile != None: tile.on_update(delta_time)
