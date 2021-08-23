import math, sys
from lux import game_constants
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate


def findOptimalResource(map, researchPoints, unit, turns_before_night):
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
    resourceMap: list[list[int]] = [[0 for c in range(width)] for r in range(height)]
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
    
    fuelCollectionMap: list[list[int]] = [[0 for c in range(width)] for r in range(height)]
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

    def abs_value(numerical_value):
        if numerical_value < 0:
            return numerical_value*-1
        else:
            return numerical_value

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
                turns_to_destination = 2*(abs_value(unit.pos.x-x) + abs_value(unit.pos.y-y))
                # closest_resource_position = find_closest_resource(Position(x, y))
                # collection_rate_closest_resource = fuelCollectionMap[closest_resource_position.x][closest_resource_position.y]
                # turns_to_closest_resource = 2*(abs_value(closest_resource_position.x-x) + abs_value(closest_resource_position.y-y))
                # value = valueFunction(fuelCollectionMap[x][y], turns_to_destination, collection_rate_closest_resource, turns_to_closest_resource)
                value = valueFunction(fuelCollectionMap[x][y], turns_to_destination)
                valueList.append((Position(x, y), value))
    
    def key(item):
        return item[1]
    return sorted(valueList, key=key, reverse=True)
    


    

