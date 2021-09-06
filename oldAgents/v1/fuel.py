import math, sys
from lux import game_constants
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

import numpy as np


def findOptimalResource(map, researchPoints, unit):
    width, height = map.width, map.height

    # returns true if in bounds
    def in_bounds(pos):
        if pos.x >= 0 and pos.x < width and pos.y >= 0 and pos.y < height:
            return True
        else:
            return False
    
    # returns arbitrary number ranking best fuel locations
    # more fuel amount is better, closer is better
    def valueFunction(fuelAmount, distance):
        return fuelAmount - 5*distance

    # maps out resource values workers can attain right now on the map

    # resourceMap: list[list[int]] = [[0 for c in range(width)] for r in range(height)]
    resourceMap = np.zeros((height, width))
    for y in range(height):
        for x in range(width):
            cell = map.get_cell(x, y)
            if cell.has_resource():
                if (cell.resource.type == RESOURCE_TYPES.WOOD):
                    resourceMap[x][y] = 20
                elif (cell.resource.type == RESOURCE_TYPES.COAL and researchPoints >= 50):
                    resourceMap[x][y] = 50
                elif (cell.resource.type == RESOURCE_TYPES.URANIUM and researchPoints >= 200):
                    resourceMap[x][y] = 80
            else:
                resourceMap[x][y] = 0
    
    # maps out for each square the amount of resources that can be mined from sitting on it
    # fuelCollectionMap: list[list[int]] = [[0 for c in range(width)] for r in range(height)]
    fuelCollectionMap = np.zeros((height, width))
    for y in range(height):
        for x in range(width):
            fuelCollectionMap[x][y] += resourceMap[x][y]
            if (in_bounds(Position(x-1, y))):
                fuelCollectionMap[x][y] += resourceMap[x - 1][y]
            if (in_bounds(Position(x+1, y))):
                fuelCollectionMap[x][y] += resourceMap[x + 1][y]
            if (in_bounds(Position(x, y - 1))):
                fuelCollectionMap[x][y] += resourceMap[x][y - 1]
            if (in_bounds(Position(x, y + 1))):
                fuelCollectionMap[x][y] += resourceMap[x][y + 1]
    
    # creates a list of pairs (a dictionary)
    # with position in the first index and its value in the second
    valueList: list[(Position, int)] = []
    for y in range(height):
        for x in range(width):
            if (fuelCollectionMap[x][y] > 0):
                turns_to_destination = 2*unit.pos.distance_to(Position(x, y))
                # closest_resource_position = find_closest_resource(Position(x, y))
                # collection_rate_closest_resource = fuelCollectionMap[closest_resource_position.x][closest_resource_position.y]
                # turns_to_closest_resource = 2*(abs(closest_resource_position.x-x) + abs(closest_resource_position.y-y))
                # value = valueFunction(fuelCollectionMap[x][y], turns_to_destination, collection_rate_closest_resource, turns_to_closest_resource)
                value = valueFunction(fuelCollectionMap[x][y], turns_to_destination)
                valueList.append((Position(x, y), value))
    
    def key(item):
        return item[1]

    # returns the valueList dictionary by value high to low
    return sorted(valueList, key=key, reverse=True)
    


    

