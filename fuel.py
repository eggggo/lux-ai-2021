import math, sys
from lux import game_constants
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate


def findOptimalResource(map, researchPoints, unit, turns_before_night, fuelCollectionMap):
    width, height = map.width, map.height

    def in_bounds(pos):
        if pos.x >= 0 and pos.x < width and pos.y >= 0 and pos.y < height:
            return True
        else:
            return False

    z = 5 # turns before night that I want to make profit by

    # def valueFunction(fuelAmount, turns_to_reach_resource, collection_rate_closest_to_resource, turns_to_closest_to_resource):
    #     return fuelAmount*(turns_before_night - z - turns_to_reach_resource-turns_to_closest_to_resource) - collection_rate_closest_to_resource*turns_to_reach_resource

    def valueFunction(fuelAmount, turns_to_reach_resource):
        return fuelAmount*(turns_before_night - z - turns_to_reach_resource) - 40*turns_to_reach_resource
    # def find_closest_resource(pos):
    #     max_dist = math.inf
    #     closest_position = Position(0, 0)
    #     for y in range(height):
    #         for x in range(width):
    #             dist = math.sqrt((pos.x-x)**2 + (pos.y-y)**2)
    #             if dist < max_dist and fuelCollectionMap[x][y] != 0:
    #                 closest_position = Position(x, y)
    #     return closest_position

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
    return sorted(valueList, key=key, reverse=True)
    


    

