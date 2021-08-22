import math, sys
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

DIRECTIONS = Constants.DIRECTIONS
game_state = None
num_cityTiles = 1 #number of cityTiles our player has
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

    ### AI Code goes down here! ### 
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

    def in_bounds(pos):
        if pos.x >= 0 and pos.x < width and pos.y >= 0 and pos.y < height:
            return True
        else:
            return False

    #list of all the positions of units to help prevent collisions
    unit_locations: list[Position] = []
    for unit in player.units:
        unit_locations.append(unit.pos)

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
            if turns_from_home > turns_until_night and closest_city_tile.pos is not None: #if the turns itll take for you to get home is greater than the turns till night, head home
                if unit.pos.translate(unit.pos.direction_to(closest_city_tile.pos), 1) not in unit_locations:
                    unit_locations.remove(unit.pos)
                    actions.append(unit.move(unit.pos.direction_to(closest_city_tile.pos)))
                    unit_locations.append(unit.pos.translate(unit.pos.direction_to(closest_city_tile.pos), 1))

            elif unit.get_cargo_space_left() == 0: #if worker has 100 cargo and assuming it is on a square it wants to build a city on
                position = unit.pos
                x_pos = position.x
                y_pos = position.y
                adjacentTiles: list[Position] = [Position(x_pos+1,y_pos), Position(x_pos-1, y_pos),
                                             Position(x_pos, y_pos+1), Position(x_pos, y_pos-1)]; #create list of adjacent tiles
                mineableAdjacentTiles: list[Position] = [Position(x_pos+1,y_pos), Position(x_pos-1, y_pos),
                                                     Position(x_pos, y_pos+1), Position(x_pos, y_pos-1)]; #create list of adjacent tiles
                collection_per_night = 0;
                accessible_fuel = 0;

                for posn in adjacentTiles: #filtering to tiles that are both adjacent and mineable
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
                    num_cityTiles = num_cityTiles + 1
                else:
                    # if unit is a worker and there is no cargo space left, and we have cities, and it is not optimal to build a city at the current tile, lets return to them
                    if closest_city_tile is not None:
                        if unit.pos.distance_to(closest_city_tile.pos) <= 1:
                            optimalFuel = max(unit.cargo.wood, unit.cargo.coal*fuel_per_unit_coal, unit.cargo.uranium*fuel_per_unit_uranium)
                            if (optimalFuel == unit.cargo.uranium*fuel_per_unit_uranium):
                                optimalResource = Constants.RESOURCE_TYPES.URANIUM
                                resourceAmount = unit.cargo.uranium
                            elif (optimalFuel == unit.cargo.coal*fuel_per_unit_coal):
                                optimalResource = Constants.RESOURCE_TYPES.COAL
                                resourceAmount = unit.cargo.coal
                            else:
                                optimalResource = Constants.RESOURCE_TYPES.WOOD
                                resourceAmount = unit.cargo.wood
                            actions.append(unit.transfer(closest_city_tile.cityid, optimalResource, resourceAmount))
                        else:
                            move_dir = unit.pos.direction_to(closest_city_tile.pos)
                            if unit.pos.translate(move_dir, 1) not in unit_locations:
                                unit_locations.remove(unit.pos)
                                actions.append(unit.move(move_dir))
                                unit_locations.append(unit.pos.translate(move_dir, 1))

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
                    if unit.pos.translate(unit.pos.direction_to(closest_resource_tile.pos), 1) not in unit_locations:
                        unit_locations.remove(unit.pos)
                        actions.append(unit.move(unit.pos.direction_to(closest_resource_tile.pos)))
                        unit_locations.append(unit.pos.translate(unit.pos.direction_to(closest_resource_tile.pos), 1))

    for name, city in player.cities.items():
        for cityTile in city.citytiles:
            if cityTile.can_act():
                if (len(player.units) < num_cityTiles) and (cityTile.pos not in unit_locations):
                    actions.append(cityTile.build_worker())
                elif player.research_points < cost_uranium:
                    actions.append(cityTile.research())

    # add in preferences for which city builds the worker depending on distance from resource

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    
    return actions


