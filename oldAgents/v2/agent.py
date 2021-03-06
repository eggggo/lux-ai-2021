import math, sys
from lux import game_constants
from lux.game import Game
from lux.game_map import Cell, RESOURCE_TYPES, Position
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate
from fuel import findOptimalResource

DIRECTIONS = Constants.DIRECTIONS
game_state = None
cost_uranium = 200 #research points needed for uranium
cost_coal = 50 #research points needed for coal
fuel_per_unit_wood = 1
fuel_per_unit_coal = 10
fuel_per_unit_uranium = 40
units_collected_per_turn_wood = 20
units_collected_per_turn_coal = 5
units_collected_per_turn_uranium = 2
full_day_night_cycle_length = 40
less_fuel_needed_per_night_constant = 5
current_default_fuel_needed_to_survive_a_full_night = 300 # if 10 nights, and 30 fuel consumed per night assuming no adj cities, 30*10 = 300
worker_cooldown = 2
night_length = 10
mining_spots = []
previous_unit_spots = {}
unit_targets = {}
build_near_city = 4

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

    # variable initialization/constants
    mining_spots = []
    estimated_total_value_of_workers = 0
    friendlyCityTiles: list[Position] = []
    num_cityTiles = 0
    unit_destinations: list[Position] = []
    minable_squares_on_map = 0
    estimated_mining_spots = []
    id_book = {}
    units_built = 0
    cities_built = 0
    list_tiles_need_city: list[Position] = []
    available: list[Position] = []  # list of available building tiles on the map
    wood_on_map = 0
    available_fuel_on_map = 0
    threshold_use_other = .4
    work_list_dictionary = {}
    cities_built_this_turn: list[Position] = []
    power_needed = 0
    power_obtained = 0
    cities_need_fuel = {} # dictionary of city_id and fuel needed
    city_adj_build_tiles = []
    sustainability_constant = 1.25
    fuel_work_list_dictionary = {}
    readily_accessible_fuel_on_map = 0

    turns_until_new_cycle = full_day_night_cycle_length - (game_state.turn % full_day_night_cycle_length)
    turns_until_night = turns_until_new_cycle - night_length
    if turns_until_night < 0:
        turns_until_night = 0

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
        options = []
        if (in_bounds((unit.pos.translate(direct, 1)))):
            distance_from_direct = ((unit.pos.translate(direct, 1)).translate(direct, 1).distance_to(tgt), direct)
            options.append(distance_from_direct)
        if (in_bounds((unit.pos.translate(rotateRight(direct), 1)))):
            distance_from_right = ((unit.pos.translate(rotateRight(direct), 1).distance_to(tgt)), rotateRight(direct))
            options.append(distance_from_right)
        if (in_bounds((unit.pos.translate(rotateLeft(direct), 1)))):
            distance_from_left = ((unit.pos.translate(rotateLeft(direct), 1).distance_to(tgt)), rotateLeft(direct))
            options.append(distance_from_left)
        sorted_options = list(sorted(options, key= lambda kv: kv[0]))
        for op in sorted_options:
            if unit.pos.translate(op[1], 1) not in unit_destinations and (unit.id not in previous_unit_spots or not previous_unit_spots[unit.id].equals(unit.pos.translate(op[1], 1))):
                return op[1]
        return DIRECTIONS.CENTER

    global previous_unit_spots
    global unit_targets
    def move(unit, tgt):
        if (closestFreeDirection(unit, tgt) != DIRECTIONS.CENTER):
            previous_unit_spots[unit.id] = unit.pos
            if unit.id in unit_targets and not tgt.equals(unit_targets[unit.id]):
                previous_unit_spots.pop(unit.id)
            unit_targets[unit.id] = tgt
            if (unit.pos not in friendlyCityTiles):
                unit_destinations.remove(unit.pos)
            action = unit.move(closestFreeDirection(unit, tgt))
            if (unit.pos.translate(closestFreeDirection(unit, tgt), 1) not in friendlyCityTiles):
                unit_destinations.append(unit.pos.translate(closestFreeDirection(unit, tgt), 1))
            return action
        else:
            if (unit.pos not in friendlyCityTiles):
                previous_unit_spots[unit.id] = unit.pos
                unit_destinations.append(unit.pos)
            return None

    def actual_distance_to(unit, tgt):
        distance = 0
        current = unit.pos
        closest_dist = current.distance_to(tgt)
        stall_turns = 0
        while (not current.equals(tgt)):
            move_dir = closestFreeDirection(current, tgt)
            current = current.translate(move_dir, 1)
            if (current.distance_to(tgt) < closest_dist):
                closest_dist = current.distance_to(tgt)
                stall_turns = 0
            else:
                stall_turns += 1
            distance += 1
            if stall_turns > 5 or move_dir == DIRECTIONS.CENTER:
                return 999
        return distance

    #given a worker's position returns the estimated fuel the worker would collect by the end of the day/night cycle
    def estimated_value_of_worker(prospective_worker):
        t = turns_until_night
        # while t > 0:
        list_of_resources = findOptimalResource(game_state.map, player.research_points, prospective_worker, turns_until_night, fuelCollectionMap)
        value = 0
        if len(list_of_resources) != 0:
            poss_posns = []
            poss_optimal_posns = []
            for pos in list_of_resources:
                poss_optimal_posns.append(pos[0])
            for posi in poss_optimal_posns:
                if posi not in estimated_mining_spots:
                    poss_posns.append(posi)
            if len(poss_posns) != 0:
                best_pos = poss_posns[0]
                estimated_mining_spots.append(best_pos)
                dist_turns = 2 * prospective_worker.pos.distance_to(best_pos)
                t -= dist_turns
                if t < 0:
                    t = 0
                value = t * fuelCollectionMap[best_pos.x][best_pos.y]
                times_back_to_city = value // 100
                t -= times_back_to_city*dist_turns
                if t < 0:
                    t = 0
                value = t * fuelCollectionMap[best_pos.x][best_pos.y]
        return value

    def closest_worker(pos):
        dictionary_workers = {}
        for worker in player.units:
            dictionary_workers[worker.id] = worker.pos.distance_to(pos)
        sorted_dictionary_workers = dict(sorted(dictionary_workers.items(), key=lambda kv: kv[1]))
        list_ids: list[str] = []
        for iden, distan in sorted_dictionary_workers.items():
            list_ids.append(iden)
        return list_ids

    def adjacent_tiles(pos):
        adjacent_tile_list_clone: list[Position] = [Position(pos.x + 1, pos.y), Position(pos.x - 1, pos.y),
                                              Position(pos.x, pos.y + 1), Position(pos.x, pos.y - 1)]
        adjacent_tile_list: list[Position] = [Position(pos.x+1, pos.y), Position(pos.x-1, pos.y),
                                              Position(pos.x, pos.y+1), Position(pos.x, pos.y-1)]
        for square in adjacent_tile_list_clone:
            if not in_bounds(square):
                adjacent_tile_list.remove(square)
        return adjacent_tile_list

    def fuel_amount(worker1):
        return worker1.cargo.wood + (worker1.cargo.coal * fuel_per_unit_coal) + (worker1.cargo.uranium * fuel_per_unit_uranium)

    def can_survive(worker2):
        nights_to_survive = 10
        if turns_until_new_cycle < 10:
            nights_to_survive = turns_until_new_cycle
        if fuel_amount(worker2) - 4 * nights_to_survive >=0:
            return True
        else:
            return False

    # add enemy citytiles to the unitLocations list to avoid collisions, added at start of turn, removed at end to make sure no carry over
    for unit in player.units:
        unit_destinations.append(unit.pos)
    for name, city in opponent.cities.items():
        for cityTiles in city.citytiles:
            unit_destinations.append(cityTiles.pos)

    for name, city in player.cities.items():
        for cityTiles in city.citytiles:
            num_cityTiles += 1
            friendlyCityTiles.append(cityTiles.pos)
            if (cityTiles.pos in unit_destinations):
                unit_destinations.remove(cityTiles.pos)

    resourceMap: list[list[int]] = [[0 for c in range(width)] for r in range(height)]
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                if (cell.resource.type == RESOURCE_TYPES.WOOD):
                    resourceMap[x][y] = 20
                elif (cell.resource.type == RESOURCE_TYPES.COAL and player.research_points >= 50):
                    resourceMap[x][y] = 50
                elif (cell.resource.type == RESOURCE_TYPES.URANIUM and player.research_points >= 200):
                    resourceMap[x][y] = 80
            else:
                resourceMap[x][y] = 0

    fuelCollectionMap: list[list[int]] = [[0 for c in range(width)] for r in range(height)]
    for y in range(height):
        for x in range(width):
            fuelCollectionMap[x][y] += resourceMap[x][y]
            if (in_bounds(Position(x - 1, y))):
                fuelCollectionMap[x][y] += resourceMap[x - 1][y]
            if (in_bounds(Position(x + 1, y))):
                fuelCollectionMap[x][y] += resourceMap[x + 1][y]
            if (in_bounds(Position(x, y - 1))):
                fuelCollectionMap[x][y] += resourceMap[x][y - 1]
            if (in_bounds(Position(x, y + 1))):
                fuelCollectionMap[x][y] += resourceMap[x][y + 1]

    for y in range(height):
        for x in range(width):
            if fuelCollectionMap[x][y] > 0:
                minable_squares_on_map += 1

    def list_pos_to_tuple(list_pos):
        list_tuple = []
        for pos in list_pos:
            list_tuple.append(tuple([pos.x, pos.y]))
        return list_tuple

    def list_tuple_to_pos(list_tuple):
        list_posi = []
        for tup in list_tuple:
            list_posi.append(Position(tup[0],tup[1]))
        return list_posi

    def can_mine(resource_cell):
        if cell.has_resource():
            if cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.research_points >= 50:
                return True
            elif cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.research_points >= 200:
                return True
            elif cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
                return True
            else:
                return False
        else:
            return False

    def create_clump(neighbor, elist):
        new_list = elist
        new_list.append(neighbor)
        adj_cell = adjacent_tiles(neighbor)
        adj_cell_copy = adjacent_tiles(neighbor)
        for neighbor_two in adj_cell_copy:
            if resourceMap[neighbor_two.x][neighbor_two.y] == 0 or neighbor_two in new_list:
                adj_cell.remove(neighbor_two)
        for neighbor_three in adj_cell:
            new_list + list_tuple_to_pos(set(list_pos_to_tuple(create_clump(neighbor_three, new_list))) - set(list_pos_to_tuple(new_list)))
        return new_list

    resource_clump_dict = {} #represents clump locations and their corresponding fuel amount.
    list_resource_clumps = [] #list of list of positions of clumps of resources
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            repeated_value = False
            for clumps in list_resource_clumps:
                if clumps is not None:
                    for pos in clumps:
                        if cell.pos.equals(pos):
                            repeated_value = True
            if can_mine(cell) and not repeated_value:
                list_resource_clumps.append(create_clump(cell.pos, []))

    def get_square_around(pos, size):
        square = []
        half = size//2
        for i in range(max(0, pos.x-half), min(pos.x+half, width)):
            for j in range(max(0, pos.y-half), min(pos.y+half, height)):
                square.append(Position(i, j))
        return square

    def value_of_nearest_clump(pos):
        for resource_clump in list_resource_clumps:
            search_tiles = get_square_around(pos, 5)
            search_tiles.append(pos)
            for position in search_tiles:
                if position in resource_clump:
                    clump_val = 0
                    for posi in resource_clump:
                        square = game_state.map.get_cell(posi.x, posi.y)
                        if square.resource.type == Constants.RESOURCE_TYPES.URANIUM:
                            clump_val += square.resource.amount * fuel_per_unit_uranium
                        elif square.resource.type == Constants.RESOURCE_TYPES.COAL:
                            clump_val += square.resource.amount * fuel_per_unit_coal
                        else:
                            clump_val += square.resource.amount
                    return resource_clump, clump_val


    workspace_countdown = minable_squares_on_map
    for unit in player.units:
        id_book[unit.id] = unit
        if workspace_countdown > 0:
            estimated_total_value_of_workers += estimated_value_of_worker(unit)
            workspace_countdown -= 1

    units_of_resource_on_map = 0
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell_by_pos(Position(x, y))
            if not cell.has_resource() and cell.citytile is None:
                available.append(Position(x, y))
            if cell.has_resource():
                if cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
                    wood_on_map += cell.resource.amount
                    available_fuel_on_map += cell.resource.amount
                    units_of_resource_on_map += cell.resource.amount
                elif cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.research_points >= 50:
                    available_fuel_on_map += cell.resource.amount*fuel_per_unit_coal
                    units_of_resource_on_map += cell.resource.amount
                elif cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.research_points >= 200:
                    available_fuel_on_map += cell.resource.amount * fuel_per_unit_uranium
                    units_of_resource_on_map += cell.resource.amount

    # if units_of_resource_on_map == 0:
    #     wood_reliance = 0
    # else:
    #     wood_reliance = 100 * wood_on_map/units_of_resource_on_map
    wood_reliance = 0

    #list of tiles with adjacent tiles of more than 1 city
    # maybe could sort this to most efficient work orders to be completed first
    for posn in available:
        adj_tile: list[Position] = adjacent_tiles(posn)
        num_adj_cities = 0
        for tiles in adj_tile:
            tiles_cell = game_state.map.get_cell_by_pos(tiles)
            if tiles_cell.citytile is not None and tiles_cell.citytile.team == game_state.id:
                num_adj_cities += 1
        if num_adj_cities >= 5:
            list_tiles_need_city.append(posn)

    if estimated_total_value_of_workers > available_fuel_on_map:
        estimated_total_value_of_workers = available_fuel_on_map

    copy_of_clump_map = list_resource_clumps
    for unit in player.units:
        if value_of_nearest_clump(unit.pos) is not None:
            place, value = value_of_nearest_clump(unit.pos)
            if place in copy_of_clump_map:
                readily_accessible_fuel_on_map += value
                copy_of_clump_map.remove(place)

    if estimated_total_value_of_workers > readily_accessible_fuel_on_map:
        estimated_total_value_of_workers = readily_accessible_fuel_on_map

    #Id of worker and position of building a city
    # use is to implement a system where when iterating through all units for their actions, can identify a unit that has a work order by its id and send it to the corresponding pos to build a city
    if len(list_tiles_need_city) != 0:
        for tiles in list_tiles_need_city:
            worker_list = closest_worker(tiles)
            for worker in worker_list:
                if not (id_book[worker].get_cargo_space_left() == 0 and id_book[worker].cargo.wood >= wood_reliance):
                    worker_list.remove(worker)
            identification = ''
            if len(worker_list) != 0:
                identification = worker_list[0]
            work_location = tiles
            if identification != '':
                work_list_dictionary[identification] = work_location
    # current city action flow:
    #   1. build workers if have space
    #   2. research otherwise
    #could potentially optimize spawn location of workers
    workers_to_build = num_cityTiles - len(player.units)
    for name, city in player.cities.items():
        night_turns_to_go = 10
        if turns_until_new_cycle < 10:
            night_turns_to_go = turns_until_new_cycle
        shortage = sustainability_constant * city.get_light_upkeep() * night_turns_to_go
        if city.fuel < shortage and len(city.citytiles) > 0:
            tuple_loc = (city.citytiles[0].pos.x, city.citytiles[0].pos.y)
            cities_need_fuel[tuple_loc] = shortage - city.fuel
        power_needed += shortage
        power_obtained += city.fuel
        for cityTile in city.citytiles:
            adj_tiles = adjacent_tiles(cityTile.pos)
            for tile in adj_tiles:
                if tile in available:
                    city_adj_build_tiles.append(tile)
            if cityTile.can_act():
                if workers_to_build > 0:
                    actions.append(cityTile.build_worker())
                    workers_to_build -= 1
                elif player.research_points < cost_uranium:
                    actions.append(cityTile.research())

    #sos system for cities to call back units that have fuel to help it survive the night
    if len(cities_need_fuel) != 0:
        for tiles, shortage_fuel in cities_need_fuel.items():
            worker_list = closest_worker(Position(tiles[0], tiles[1]))
            copy_worker_list = closest_worker(Position(tiles[0], tiles[1]))
            for worker in copy_worker_list:
                if (not (fuel_amount(id_book[worker]) >= 80)):
                    worker_list.remove(worker)
                elif (worker in fuel_work_list_dictionary):
                    worker_list.remove(worker)
                elif (id_book[worker].pos.distance_to(Position(tiles[0], tiles[1])) > 7 ):
                    worker_list.remove(worker)

            fuel_to_make_up = shortage_fuel
            while fuel_to_make_up > 0 and len(worker_list) != 0:
                identification = ''
                if len(worker_list) != 0:
                    identification = worker_list[0]
                work_location = Position(tiles[0], tiles[1])
                if identification != '':
                    fuel_work_list_dictionary[identification] = work_location
                    fuel_to_make_up -= fuel_amount(id_book[worker_list[0]])
                    worker_list.remove(worker_list[0])


    # we iterate over all our units and do something with them
    for unit in player.units:
        if unit.is_worker() and unit.can_act():
            workerActioned = False
            # if there is a work order for the unit to build somewhere, go there and build
            if unit.id in work_list_dictionary and not workerActioned:
                if unit.pos.equals(work_list_dictionary[unit.id]) and unit.can_build(game_state.map):
                    actions.append(unit.build_city())
                    available.remove(unit.pos)
                    cities_built_this_turn.append(unit.pos)
                    workerActioned = True
                else:
                    action = move(unit, work_list_dictionary[unit.id])
                    if action is not None:
                        actions.append(action)
                        workerActioned = True
            closest_dist_city = math.inf
            closest_city_tile = None
            if len(player.cities) > 0:
                for k, city in player.cities.items():
                    for city_tile in city.citytiles:
                        dist = city_tile.pos.distance_to(unit.pos)
                        if dist < closest_dist_city:
                            closest_dist_city = dist
                            closest_city_tile = city_tile
            turns_from_home = closest_dist_city * worker_cooldown
            # if the worker is a target for the sos system, go help the city who needs it
            if unit.id in fuel_work_list_dictionary and not workerActioned:
                action = move(unit, fuel_work_list_dictionary[unit.id])
                if action is not None:
                    actions.append(action)
                    workerActioned = True
            # if night is approaching and you close and can't survive alone, go home
            elif turns_from_home >= turns_until_night and closest_city_tile is not None and unit.pos.distance_to(closest_city_tile.pos) < 7 and not can_survive(unit) and not workerActioned: #if the turns itll take for you to get home is greater than the turns till night, head home
                action = move(unit, closest_city_tile.pos)
                if (action != None):
                    actions.append(action)
                    workerActioned = True
            # OTHERWISE if you have reached full capacity collecitng
            elif unit.get_cargo_space_left() == 0:
                if (not workerActioned):
                    #if you can build on the current tile
                    if (estimated_total_value_of_workers + estimated_value_of_worker(unit) + power_obtained >= power_needed + 200 + 200*cities_built) and unit.cargo.wood >= wood_reliance and unit.cargo.uranium != 100 and unit.can_build(game_state.map):
                        #if this current tile is already next to a city, just build it
                        if unit.pos in city_adj_build_tiles and not workerActioned:
                            actions.append(unit.build_city())
                            available.remove(unit.pos)
                            cities_built_this_turn.append(unit.pos)
                            units_built += 1
                            cities_built += 1
                            workerActioned = True
                        # if theres another city close by, just go attach onto that city to save resource
                        elif closest_city_tile is not None and unit.pos.distance_to(closest_city_tile.pos) <= build_near_city and not workerActioned:
                            def closest_tile(posi):
                                return unit.pos.distance_to(posi)
                            city_adj_build_tiles.sort(key=closest_tile)
                            if len(city_adj_build_tiles) != 0:
                                unit_destinations.extend(friendlyCityTiles)
                                action = move(unit, city_adj_build_tiles[0])
                                for destination in friendlyCityTiles:
                                    if destination in unit_destinations:
                                        unit_destinations.remove(destination)
                                if action != None:
                                    actions.append(action)
                                    workerActioned = True
                        # otherwise if no city close by just build city by itself
                        elif not workerActioned:
                            actions.append(unit.build_city())
                            available.remove(unit.pos)
                            cities_built_this_turn.append(unit.pos)
                            units_built += 1
                            cities_built += 1
                            workerActioned = True
                    #if the unit cannot build in this particular spot but is still at full cargo
                    elif (estimated_total_value_of_workers + estimated_value_of_worker(unit) >= power_needed + 200 + 200*cities_built) and unit.cargo.wood >= wood_reliance and unit.cargo.uranium != 100 and not unit.can_build(game_state.map):
                        # go to the closest adjacent city tile if it is close
                        if closest_city_tile is not None and unit.pos.distance_to(closest_city_tile.pos) <= build_near_city and not workerActioned:
                            def closest_tile(posi):
                                return unit.pos.distance_to(posi)
                            city_adj_build_tiles.sort(key=closest_tile)
                            if len(city_adj_build_tiles) != 0:
                                unit_destinations.extend(friendlyCityTiles)
                                action = move(unit, city_adj_build_tiles[0])
                                for destination in friendlyCityTiles:
                                    if destination in unit_destinations:
                                        unit_destinations.remove(destination)
                                if (action != None):
                                    actions.append(action)
                                    workerActioned = True
                        # otherwise find the closest free resource spot to go to
                        elif not workerActioned:
                            estimated_total_value_of_workers += estimated_value_of_worker(unit) # delete?
                            best_mining_locations = findOptimalResource(game_state.map, player.research_points, unit, turns_until_night, fuelCollectionMap)
                            optimal_location: list[Position] = []
                            for loc in best_mining_locations:
                                optimal_location.append(loc[0])
                            perfect_place: list[Position] = []
                            for loc in optimal_location:
                                if (loc in available) and (loc not in unit_destinations):
                                    perfect_place.append(loc)
                            if len(perfect_place) != 0:
                                action = move(unit, perfect_place[0])
                                if (action != None):
                                   actions.append(action)
                                   workerActioned = True
                    else:
                        # if unit is a worker and there is no cargo space left, and we have cities, and it is not optimal to build a city at the current tile, lets return to them
                        if closest_city_tile is not None:
                            action = move(unit, closest_city_tile.pos)
                            if (action != None):
                                actions.append(action)
                                workerActioned = True
            # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it but better
            # if unit has space left
            elif unit.get_cargo_space_left() > 0 and not workerActioned:
                possibleGatheringPositions = findOptimalResource(game_state.map, player.research_points, unit,
                                                                 turns_until_night, fuelCollectionMap)
                # if we can sustain a new city move off a city tile to go to closest free resource spot
                if unit.pos in friendlyCityTiles and (estimated_total_value_of_workers + estimated_value_of_worker(unit) >= power_needed + 200 + 200*cities_built) and unit.cargo.uranium != 100:
                    if not workerActioned:
                        estimated_total_value_of_workers += estimated_value_of_worker(unit)  # delete?
                        best_mining_locations = findOptimalResource(game_state.map, player.research_points, unit,
                                                                    turns_until_night, fuelCollectionMap)
                        optimal_location: list[Position] = []
                        for loc in best_mining_locations:
                            optimal_location.append(loc[0])
                        perfect_place: list[Position] = []
                        for loc in optimal_location:
                            if (loc in available) and (loc not in unit_destinations):
                                perfect_place.append(loc)
                        if len(perfect_place) != 0:
                            action = move(unit, perfect_place[0])
                            if (action != None):
                                actions.append(action)
                                workerActioned = True
                elif not workerActioned and (len(possibleGatheringPositions) > 0) and (estimated_total_value_of_workers + estimated_value_of_worker(unit) >= power_needed + 200 + 200*cities_built) and unit.cargo.uranium != 100:
                    gathering_locs: list[Position] = []
                    for pgp in possibleGatheringPositions:
                        gathering_locs.append(pgp[0])
                    for spot in mining_spots:
                        if spot in gathering_locs:
                            gathering_locs.remove(spot)
                    if len(gathering_locs) != 0:
                        optimal_location = gathering_locs[0]
                        unit_destinations.extend(friendlyCityTiles)
                        action = move(unit, optimal_location)
                        for destination in friendlyCityTiles:
                            if destination in unit_destinations:
                                unit_destinations.remove(destination)
                        if action != None:
                            actions.append(action)
                            mining_spots.append(optimal_location)
                            workerActioned = True
                        else:
                            mining_spots.append(unit.pos)
                elif not workerActioned and (len(possibleGatheringPositions) > 0):
                    gathering_locs: list[Position] = []
                    for pgp in possibleGatheringPositions:
                        gathering_locs.append(pgp[0])
                    for spot in mining_spots:
                        if spot in gathering_locs:
                            gathering_locs.remove(spot)
                    if len(gathering_locs) != 0:
                        optimal_location = gathering_locs[0]
                        action = move(unit, optimal_location)
                        if action != None:
                            actions.append(action)
                            mining_spots.append(optimal_location)
                            workerActioned = True
                        else:
                            mining_spots.append(unit.pos)
    # add in preferences for which city builds the worker depending on distance from resource

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))
    # print(game_state.turn)
    # print(power_needed)
    # print(estimated_total_value_of_workers)
    # print(readily_accessible_fuel_on_map)
    return actions


