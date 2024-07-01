from prp.solvers.simple import CheapestPlaceSolver, CostsType, RandomSolver
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils
import json
import numpy as np
import prp.core.costs as costs_mod
import random

# region set directories
LAYOUT_FILE = "data/10-layout.json"
INITIAL_STATE_FILE = "data/10-initial-state.json"
DEPARTURES_FILE = "data/10-departures.json"
SOLUTION_FILE = "data/solutions/10-cheapest-place-solution.json"

def load_problem():
    """Load a test system with 10 places and 10 pods randomly distributed among them."""
    layout = xy.Layout()
    with open(LAYOUT_FILE, 'r') as infile:
        layout.load_from_json(infile)
        warehouse = layout.get_empty_warehouse()
        costs = layout.get_costs()
        print(costs)
        warehouse.set_costs(costs)
    with open(INITIAL_STATE_FILE, 'r') as infile:
        recorder.load_initial_state_from_json(infile, warehouse)
    with open(DEPARTURES_FILE, 'r') as infile:
        departures = recorder.load_departures_from_json(infile)
        warehouse.set_departure_generator(departures)
    return warehouse

# Initial solution
warehouse = load_problem()
# endregion

# Select solver
solver = CheapestPlaceSolver(warehouse, costs_type=CostsType.DECISION)
solver2 = RandomSolver(warehouse)

# Initialize arrays
iterations = 1000
x = 0
solution = []
costs = np.empty(iterations, dtype=int)
pod_location = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
Original_Configuration = np.empty((iterations, 10), dtype=int)
Next_Configuration = np.empty((iterations, 10), dtype=int)
Original_Configuration[x] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# region initial solution with cheapest place    
while not warehouse.finished():
    place_id, pod, station_id = solver.decide_new_place()
    solution.append(place_id)
    
    # Store movements in arrays in order to use in heuristic
    previous_location = pod_location[pod - 1]
    Next_Configuration[x] = Original_Configuration[x]
    Next_Configuration[x][previous_location - 1] = 0
    Next_Configuration[x][place_id - 1] = pod
    pod_location[pod - 1] = place_id
    
    # Can only store costs if a movement is made
    if place_id != 0 and previous_location != 0:
        costs[x] = warehouse.costs.from_station(station_id, place_id) + warehouse.costs.to_station(previous_location, station_id)
   
    # Cannot store configurations in the last iteration
    if x != iterations - 1:
        Original_Configuration[x + 1] = Next_Configuration[x]
    x += 1
    warehouse.next(place_id)
# endregion

def generate_neighbor_solution(solution):
    warehouse2 = warehouse
    randomindex = np.random.randint(len(solution))
    newsolution = solution[:randomindex]
    firstpass = True

    x = randomindex 
    while len(newsolution) <= iterations - 1:
        if firstpass:
            place_id, pod, station_id = solver2.decide_new_place()
            firstpass = False
        else:
            place_id, pod, station_id = solver.decide_new_place()

        newsolution.append(place_id)
        # Can only store costs if a movement is made
        if place_id != 0 and previous_location != 0:
            costs[x] = warehouse2.costs.from_station(station_id, place_id) + warehouse2.costs.to_station(previous_location, station_id)

        # Cannot store configurations in the last iteration
        if x != iterations - 1:
            Original_Configuration[x + 1] = Next_Configuration[x]
        x += 1
        warehouse2.next(place_id)

    return newsolution

# Simulated annealing parameters
initial_temperature = 100
cooling_rate = 0.99
markov_chain_length = 100
min_temp = 1
current_temp = initial_temperature

# Simulated annealing algorithm
best_solution = solution
best_cost = np.sum(costs)
current_solution = solution
current_cost = best_cost

while current_temp > min_temp:
    for i in range(markov_chain_length):
        neighbor_solution = generate_neighbor_solution(current_solution)
        neighbor_cost = np.sum(costs)
        
        if neighbor_cost < current_cost:
            current_solution = neighbor_solution
            current_cost = neighbor_cost
            if neighbor_cost < best_cost:
                best_solution = neighbor_solution
                best_cost = neighbor_cost
        else:
            r = np.random.random()
            if r < np.exp((current_cost - neighbor_cost) / current_temp):
                current_solution = neighbor_solution
                current_cost = neighbor_cost

    current_temp = current_temp * cooling_rate

# Print results
print("Initial solution:", solution)
print("Optimized solution:", best_solution)
print("Initial total cost: {} at time {}.".format(np.sum(costs), warehouse.t))
print("Optimized total cost:", best_cost)

# Save solution to a JSON file.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(best_solution, outfile)