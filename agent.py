import math, sys
from lux import game_constants
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

DIRECTIONS = Constants.DIRECTIONS
game_state = None
cost_uranium = 200 #research points needed for uranium
cost_coal = 50 #research points needed for coal
fuel_per_unit_wood = 1
fuel_per_unit_coal = 5
fuel_per_unit_uranium = 20
units_collected_per_turn_wood = 20
units_collected_per_turn_coal = 10
units_collected_per_turn_uranium = 4
full_day_night_cycle_length = 40
less_fuel_needed_per_night_constant = 5
current_default_fuel_needed_to_survive_a_full_night = 300 # if 10 nights, and 30 fuel consumed per night assuming no adj cities, 30*10 = 300
worker_cooldown = 2
night_length = 10

def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []

    ### AI Code goes down here! ### s
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height
    turns_until_night = full_day_night_cycle_length - (game_state.turn % full_day_night_cycle_length) - night_length
    if turns_until_night < 0:
        turns_until_night = 0

    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            # make sure wood doesn't deplete.  Logic for the number 2 is that by moving adj to the square,
            # you have a cooldown of two and will passively collect that, depleting the resource if the amount left is less than two times the collection rate
            # if cell.has_resource() and not (cell.resource.type == Constants.RESOURCE_TYPES.WOOD and cell.resource.amount < 2 * units_collected_per_turn_wood):
            if cell.has_resource():
                resource_tiles.append(cell)
    
    # add enemy citytiles to the unitLocations list to avoid collisions, added at start of turn, removed at end to make sure no carry over
    unit_destinations: list[Position] = []
    for unit in player.units:
        unit_destinations.append(unit.pos)
    for name, city in opponent.cities.items():
        for cityTiles in city.citytiles:
            unit_destinations.append(cityTiles.pos)

    num_cityTiles = 0
    #count number of city tiles owned per turn.
    for name, city in player.cities.items():
        for cityTiles in city.citytiles:
            num_cityTiles += 1

    def in_bounds(pos):
        if pos.x >= 0 and pos.x < width and pos.y >= 0 and pos.y < height:
            return True
        else:
            return False

    def rotateRight(dir):
        if (dir == DIRECTIONS.CENTER):
            return DIRECTIONS.CENTER
        elif (dir == DIRECTIONS.NORTH):
            return DIRECTIONS.EAST
        elif (dir == DIRECTIONS.EAST):
            return DIRECTIONS.SOUTH
        elif (dir == DIRECTIONS.SOUTH):
            return DIRECTIONS.WEST
        else:
            return DIRECTIONS.NORTH

    def rotateLeft(dir):
        if (dir == DIRECTIONS.CENTER):
            return DIRECTIONS.CENTER
        elif (dir == DIRECTIONS.NORTH):
            return DIRECTIONS.WEST
        elif (dir == DIRECTIONS.EAST):
            return DIRECTIONS.NORTH
        elif (dir == DIRECTIONS.SOUTH):
            return DIRECTIONS.EAST
        else:
            return DIRECTIONS.SOUTH

    def closestFreeDirection(unit, tgt):
        direct = unit.pos.direction_to(tgt)
        if (unit.pos.translate(direct, 1) not in unit_destinations):
            return direct
        else:
            if (unit.pos.translate(rotateRight(direct), 1) not in unit_destinations and in_bounds(unit.pos.translate(rotateRight(direct), 1))):
                return rotateRight(direct)
            elif (unit.pos.translate(rotateLeft(direct), 1) not in unit_destinations and in_bounds(unit.pos.translate(rotateLeft(direct), 1))):
                return rotateLeft(direct)
            elif (unit.pos.translate(rotateRight(rotateRight(direct)), 1) not in unit_destinations and in_bounds(unit.pos.translate(rotateRight(rotateRight(direct)), 1))):
                return rotateRight(rotateRight(direct))
            else:
                return DIRECTIONS.CENTER

    def move(unit, tgt):
        if (unit.pos.translate(unit.pos.direction_to(tgt), 1) not in unit_destinations):
            action = unit.move(unit.pos.direction_to(tgt))
            unit_destinations.append(unit.pos.translate(unit.pos.direction_to(tgt), 1))
            return action
        elif (closestFreeDirection(unit, tgt) != DIRECTIONS.CENTER):
            action = unit.move(closestFreeDirection(unit, tgt))
            unit_destinations.append(unit.pos.translate(closestFreeDirection(unit, tgt), 1))
            return action
        else:
            unit_destinations.append(unit.pos)
            return None

    # current city action flow:
    #   1. build workers if have space
    #   2. research otherwise
    for name, city in player.cities.items():
        for cityTile in city.citytiles:
            if cityTile.can_act():
                if (len(player.units) < num_cityTiles):
                    actions.append(cityTile.build_worker())
                elif player.research_points < cost_uranium:
                    actions.append(cityTile.research())

    # we iterate over all our units and do something with them
    for unit in player.units:
        if unit.is_worker() and unit.can_act():
            closest_dist_city = math.inf
            closest_city_tile = None
            closest_dist_resource = math.inf
            closest_resource_tile = None
            if len(player.cities) > 0:
                for k, city in player.cities.items():
                    for city_tile in city.citytiles:
                        dist = city_tile.pos.distance_to(unit.pos)
                        if dist < closest_dist_city:
                            closest_dist_city = dist
                            closest_city_tile = city_tile
            turns_from_home = closest_dist_city * worker_cooldown
            # current action flow listed off priority: 
            #   1. go home if close to night
            #   2. build city if sustainable and have 100 resource
            #   3. if didn't build city go to nearest city to depo
            #   4. collect resources if >90 cargo space
            if turns_from_home >= turns_until_night and closest_city_tile is not None: #if the turns itll take for you to get home is greater than the turns till night, head home
                action = move(unit, closest_city_tile.pos)
                if (action != None):
                    actions.append(action)
            elif unit.get_cargo_space_left() == 0: #if worker has 100 cargo and assuming it is on a square it wants to build a city on
                position = unit.pos
                x_pos = position.x
                y_pos = position.y
                copyAdjacentTiles: list[Position] = [Position(x_pos+1,y_pos), Position(x_pos-1, y_pos),
                                             Position(x_pos, y_pos+1), Position(x_pos, y_pos-1)] #create copy of list of adjacent tiles
                adjacentTiles: list[Position] = [Position(x_pos+1,y_pos), Position(x_pos-1, y_pos),
                                             Position(x_pos, y_pos+1), Position(x_pos, y_pos-1)] #create list of adjacent tiles
                adjacentTiles = list(filter(lambda pos: in_bounds(pos), adjacentTileOptions))
                mineableAdjacentTileOptions: list[Position] = [Position(x_pos+1,y_pos), Position(x_pos-1, y_pos),
                                                     Position(x_pos, y_pos+1), Position(x_pos, y_pos-1)] #create list of adjacent tiles
                mineableAdjacentTiles = list(filter(lambda pos: in_bounds(pos), mineableAdjacentTileOptions))
                collection_per_night = 0
                accessible_fuel = 0

                for posn in copyAdjacentTiles: #filtering to tiles that are both adjacent and mineable
                    if not in_bounds(posn): #filter adjacent tiles to the in bounds tiles
                        adjacentTiles.remove(posn)
                        mineableAdjacentTiles.remove(posn)
                    else:
                        cell = game_state.map.get_cell_by_pos(posn)
                        if cell.has_resource(): #filter adjacent tiles to the mineable adjacent tiles
                            if player.researched_uranium() and cell.resource.type == Constants.RESOURCE_TYPES.URANIUM:
                                # check if resource is about to be depleted in order to get an accurate count of collection rate
                                if cell.resource.amount < units_collected_per_turn_uranium:
                                    collection_per_night += cell.resource.amount * fuel_per_unit_uranium
                                    accessible_fuel += cell.resource.amount * fuel_per_unit_uranium
                                else:
                                    collection_per_night += units_collected_per_turn_uranium * fuel_per_unit_uranium
                                    accessible_fuel += cell.resource.amount * fuel_per_unit_uranium
                            elif player.researched_coal() and cell.resource.type == Constants.RESOURCE_TYPES.COAL:
                                # check if resource is about to be depleted in order to get an accurate count of collection rate
                                if cell.resource.amount < units_collected_per_turn_coal:
                                    collection_per_night += cell.resource.amount * fuel_per_unit_coal
                                    accessible_fuel += cell.resource.amount * fuel_per_unit_coal
                                else:
                                    collection_per_night += units_collected_per_turn_coal * fuel_per_unit_coal
                                    accessible_fuel += cell.resource.amount * fuel_per_unit_coal
                            elif cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
                                # check if resource is about to be depleted in order to get an accurate count of collection rate
                                if cell.resource.amount < units_collected_per_turn_wood:
                                    collection_per_night += cell.resource.amount * fuel_per_unit_wood
                                    accessible_fuel += cell.resource.amount * fuel_per_unit_wood
                                else:
                                    collection_per_night += units_collected_per_turn_wood * fuel_per_unit_wood
                                    accessible_fuel += cell.resource.amount * fuel_per_unit_wood
                        else:
                            mineableAdjacentTiles.remove(posn)
                necessary_fuel_to_keep_city_alive = current_default_fuel_needed_to_survive_a_full_night
                for tile in adjacentTiles:
                    cell = game_state.map.get_cell_by_pos(tile)
                    if (cell.citytile is not None) and cell.citytile.cityid == game_state.id:
                        necessary_fuel_to_keep_city_alive -= less_fuel_needed_per_night_constant
                if (turns_until_night * collection_per_night > necessary_fuel_to_keep_city_alive/10 and \
                        accessible_fuel > necessary_fuel_to_keep_city_alive/10) and unit.can_build(game_state.map):
                    actions.append(unit.build_city())
                else:
                    # if unit is a worker and there is no cargo space left, and we have cities, and it is not optimal to build a city at the current tile, lets return to them
                    if closest_city_tile is not None:
                        action = move(unit, closest_city_tile.pos)
                        if (action != None):
                            actions.append(action)

            elif unit.get_cargo_space_left() > 90:
                # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it
                for resource_tile in resource_tiles:
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal(): continue
                    if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium(): continue
                    dist = resource_tile.pos.distance_to(unit.pos)
                    if dist < closest_dist_resource:
                        closest_dist_resource = dist
                        closest_resource_tile = resource_tile
                if closest_resource_tile is not None:
                    action = move(unit, closest_resource_tile.pos)
                    if (action != None):
                        actions.append(action)

    # add in preferences for which city builds the worker depending on distance from resource

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    
    return actions


