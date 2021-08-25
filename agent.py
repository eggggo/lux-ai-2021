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
wood_on_map_initial = 0
mining_spots = []

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

    turns_until_new_cycle = full_day_night_cycle_length - (game_state.turn % full_day_night_cycle_length)
    turns_until_night = turns_until_new_cycle - night_length
    if turns_until_night < 0:
        turns_until_night = 0

    # clumping
    mining_spots = []

    # add enemy citytiles to the unitLocations list to avoid collisions, added at start of turn, removed at end to make sure no carry over
    unit_destinations: list[Position] = []
    for unit in player.units:
        unit_destinations.append(unit.pos)
    for name, city in opponent.cities.items():
        for cityTiles in city.citytiles:
            unit_destinations.append(cityTiles.pos)

    friendlyCityTiles: list[Position] = []
    num_cityTiles = 0
    for name, city in player.cities.items():
        for cityTiles in city.citytiles:
            num_cityTiles +=1
            friendlyCityTiles.append(cityTiles.pos)
            if (cityTiles.pos in unit_destinations):
                unit_destinations.remove(cityTiles.pos)

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
            options = []
            if (in_bounds((unit.pos.translate(rotateRight(direct), 1)))):
                distance_from_right = ((unit.pos.translate(rotateRight(direct), 1).distance_to(tgt)), rotateRight(direct))
                options.append(distance_from_right)
            if (in_bounds((unit.pos.translate(rotateLeft(direct), 1)))):
                distance_from_left = ((unit.pos.translate(rotateLeft(direct), 1).distance_to(tgt)), rotateLeft(direct))
                options.append(distance_from_left)
            if (in_bounds((unit.pos.translate(rotateRight(rotateRight(direct)), 1)))):
                distance_from_back = ((unit.pos.translate(rotateRight(rotateRight(direct)), 1).distance_to(tgt)), rotateRight(rotateRight(direct)))
                options.append(distance_from_back)
            sorted_options = list(sorted(options, key= lambda kv: kv[0]))
            for op in sorted_options:
                if unit.pos.translate(op[1], 1) not in unit_destinations:
                    return op[1]
            return DIRECTIONS.CENTER
            # if (unit.pos.translate(rotateRight(direct), 1) not in unit_destinations and in_bounds(unit.pos.translate(rotateRight(direct), 1))):
            #     return rotateRight(direct)
            # elif (unit.pos.translate(rotateLeft(direct), 1) not in unit_destinations and in_bounds(unit.pos.translate(rotateLeft(direct), 1))):
            #     return rotateLeft(direct)
            # elif (unit.pos.translate(rotateRight(rotateRight(direct)), 1) not in unit_destinations and in_bounds(unit.pos.translate(rotateRight(rotateRight(direct)), 1))):
            #     return rotateRight(rotateRight(direct))
            # else:
            #     return DIRECTIONS.CENTER

    def move(unit, tgt):
        if (unit.pos.translate(unit.pos.direction_to(tgt), 1) not in unit_destinations):
            if (unit.pos not in friendlyCityTiles):
                unit_destinations.remove(unit.pos)
            action = unit.move(unit.pos.direction_to(tgt))
            if (unit.pos.translate(unit.pos.direction_to(tgt), 1) not in friendlyCityTiles):
                unit_destinations.append(unit.pos.translate(unit.pos.direction_to(tgt), 1))
            return action
        elif (closestFreeDirection(unit, tgt) != DIRECTIONS.CENTER):
            if (unit.pos not in friendlyCityTiles):
                unit_destinations.remove(unit.pos)
            action = unit.move(closestFreeDirection(unit, tgt))
            if (unit.pos.translate(closestFreeDirection(unit, tgt), 1) not in friendlyCityTiles):
                unit_destinations.append(unit.pos.translate(closestFreeDirection(unit, tgt), 1))
            return action
        else:
            if (unit.pos not in friendlyCityTiles):
                unit_destinations.append(unit.pos)
            return None

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
    minable_squares_on_map = 0
    for y in range(height):
        for x in range(width):
            if fuelCollectionMap[x][y] > 0:
                minable_squares_on_map += 1

    #given a worker's position returns the estimated fuel the worker would collect by the end of the day/night cycle
    estimated_mining_spots = []
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

    estimated_total_value_of_workers = 0

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

    id_book = {}
    workspace_countdown = minable_squares_on_map
    for unit in player.units:
        id_book[unit.id] = unit
        if workspace_countdown > 0:
            estimated_total_value_of_workers += estimated_value_of_worker(unit)
            workspace_countdown -= 1
    units_built = 0
    cities_built = 1

    #list of available building tiles on the map
    available: list[Position] = []
    wood_on_map = 0
    available_fuel_on_map = 0
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell_by_pos(Position(x, y))
            if not cell.has_resource() and cell.citytile is None:
                available.append(Position(x, y))
            if cell.has_resource():
                if cell.resource.type == Constants.RESOURCE_TYPES.WOOD:
                    wood_on_map += cell.resource.amount
                    available_fuel_on_map += cell.resource.amount
                elif cell.resource.type == Constants.RESOURCE_TYPES.COAL and player.research_points >= 50:
                    available_fuel_on_map += cell.resource.amount*fuel_per_unit_coal
                elif cell.resource.type == Constants.RESOURCE_TYPES.URANIUM and player.research_points >= 200:
                    available_fuel_on_map += cell.resource.amount * fuel_per_unit_uranium
    global wood_on_map_initial
    if game_state.turn == 0:
        wood_on_map_initial = wood_on_map
    threshold_use_other = .4
    wood_reliance = 80
    if wood_on_map_initial*threshold_use_other >= wood_on_map:
        wood_reliance = 0
    #list of tiles with adjacent tiles of more than 1 city
    # maybe could sort this to most efficient work orders to be completed first
    list_tiles_need_city: list[Position] = []
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

    #Id of worker and position of building a city
    # use is to implement a system where when iterating through all units for their actions, can identify a unit that has a work order by its id and send it to the corresponding pos to build a city
    work_list_dictionary = {}
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

    cities_built_this_turn: list[Position] = []

    workers_to_build = num_cityTiles - len(player.units)
    power_needed = 0
    power_obtained = 0
    #dictionary of city_id and fuel needed
    cities_need_fuel = {}
    city_adj_build_tiles = []

    sustainability_constant = 1.2

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

    def fuel_amount(worker1):
        return worker1.cargo.wood + (worker1.cargo.coal * fuel_per_unit_coal) + (worker1.cargo.uranium * fuel_per_unit_uranium)


    fuel_work_list_dictionary = {}
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
            if unit.id in fuel_work_list_dictionary and not workerActioned:
                action = move(unit, fuel_work_list_dictionary[unit.id])
                if action is not None:
                    actions.append(action)
                    workerActioned = True
            elif turns_from_home >= turns_until_night and closest_city_tile is not None and unit.pos.distance_to(closest_city_tile.pos) < 7 and not workerActioned: #if the turns itll take for you to get home is greater than the turns till night, head home
                action = move(unit, closest_city_tile.pos)
                if (action != None):
                    actions.append(action)
                    workerActioned = True
            elif unit.get_cargo_space_left() == 0: #if worker has 100 cargo and assuming it is on a square it wants to build a city on
                position = unit.pos
                x_pos = position.x
                y_pos = position.y
                adjacentTileOptions: list[Position] = [Position(x_pos+1,y_pos), Position(x_pos-1, y_pos),
                                             Position(x_pos, y_pos+1), Position(x_pos, y_pos-1)] #create list of adjacent tiles
                adjacentTiles = list(filter(lambda pos: in_bounds(pos), adjacentTileOptions))
                mineableAdjacentTileOptions: list[Position] = [Position(x_pos+1,y_pos), Position(x_pos-1, y_pos),
                                                     Position(x_pos, y_pos+1), Position(x_pos, y_pos-1)] #create list of adjacent tiles
                mineableAdjacentTiles = list(filter(lambda pos: in_bounds(pos), mineableAdjacentTileOptions))

                if (not workerActioned):
                    #if turns_until_night > building_constant_a and unit.cargo.wood >= 80 and unit.can_build(game_state.map):
                        #actions.append(unit.build_city())
                        #workerActioned = True
                    # if (turns_until_new_cycle * collection_per_night > necessary_fuel_to_keep_city_alive/building_constant_b and \
                    #     accessible_fuel > necessary_fuel_to_keep_city_alive/building_constant_c) and unit.cargo.wood >= 80 and unit.can_build(game_state.map): #might be able to further optimize sustainability function to build during night?
                    #     actions.append(unit.build_city())
                    #     workerActioned = True
                    if (estimated_total_value_of_workers + estimated_value_of_worker(unit) + power_obtained >= power_needed + 20*cities_built) and unit.cargo.wood >= wood_reliance and unit.cargo.uranium != 100 and unit.can_build(game_state.map):
                        # if closest_city_tile is not None:
                        #     if unit.pos.distance_to(closest_city_tile.pos) == 2:
                        #         adjacent_tiles_to_unit = adjacent_tiles(unit.pos)
                        #         possible_movements: list[Position] = []
                        #         for tile in adjacent_tiles_to_unit:
                        #             if closest_city_tile.pos.distance_to(tile) == 1 and (tile in available):
                        #                 possible_movements.append(tile)
                        #         if len(possible_movements) != 0:
                        #             action = move(unit, possible_movements[0])
                        #             if (action != None):
                        #                 actions.append(action)
                        #                 workerActioned = True
                        if unit.pos in city_adj_build_tiles and not workerActioned:
                            actions.append(unit.build_city())
                            available.remove(unit.pos)
                            cities_built_this_turn.append(unit.pos)
                            units_built += 1
                            cities_built += 1
                            workerActioned = True
                        elif closest_city_tile is not None and unit.pos.distance_to(closest_city_tile.pos) <= 5 and not workerActioned:
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

                        elif not workerActioned:
                            actions.append(unit.build_city())
                            available.remove(unit.pos)
                            cities_built_this_turn.append(unit.pos)
                            units_built += 1
                            cities_built += 1
                            workerActioned = True
                    elif (estimated_total_value_of_workers + estimated_value_of_worker(unit) >= power_needed + 200*cities_built) and unit.cargo.wood >= wood_reliance and unit.cargo.uranium != 100 and not unit.can_build(game_state.map):
                        # if closest_city_tile is not None:
                        #     if unit.pos.distance_to(closest_city_tile.pos) == 2:
                        #         adjacent_tiles_to_unit = adjacent_tiles(unit.pos)
                        #         possible_movements: list[Position] = []
                        #         for tile in adjacent_tiles_to_unit:
                        #             if closest_city_tile.pos.distance_to(tile) == 1 and (tile in available):
                        #                 possible_movements.append(tile)
                        #         if len(possible_movements) != 0:
                        #             action = move(unit, possible_movements[0])
                        #             if (action != None):
                        #                 actions.append(action)
                        #                 workerActioned = True
                        if closest_city_tile is not None and unit.pos.distance_to(closest_city_tile.pos) <= 5 and not workerActioned:
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
                        elif not workerActioned:
                            estimated_total_value_of_workers += estimated_value_of_worker(unit)
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

            elif unit.get_cargo_space_left() > 0 and not workerActioned:
                # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it but better
                possibleGatheringPositions = findOptimalResource(game_state.map, player.research_points, unit, turns_until_night, fuelCollectionMap)
                if (len(possibleGatheringPositions) > 0):
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
    # print(power_needed + 20*cities_built)
    # print(estimated_total_value_of_workers)
    return actions


