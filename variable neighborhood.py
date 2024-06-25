import json
import numpy as np
import prp.core.costs as costs_mod
from prp.solvers.simple import CheapestPlaceSolver, CostsType
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils
import random

#region set directories
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
        warehouse.set_costs(costs)
    with open(INITIAL_STATE_FILE, 'r') as infile:
        recorder.load_initial_state_from_json(infile, warehouse)
    with open(DEPARTURES_FILE, 'r') as infile:
        departures = recorder.load_departures_from_json(infile)
        warehouse.set_departure_generator(departures)
    return warehouse

def initialize_adaptive_strategy():
    weights = {'destroy_method1': 1.0, 'destroy_method2': 1.0, 'repair_method1': 1.0, 'repair_method2': 1.0}
    probabilities = {k: 1/len(weights) for k in weights}
    return weights, probabilities

def select_method(adaptive_strategy, methods):
    probabilities = list(adaptive_strategy.values())
    selected_method = random.choices(methods, weights=probabilities, k=1)[0]
    return selected_method

def destroy_solution(solution, method):
    # Placeholder for destruction logic based on the selected method
    return solution

def repair_solution(solution, method):
    # Placeholder for repair logic based on the selected method
    return solution

def update_adaptive_strategy(weights, probabilities, method, success):
    if success:
        weights[method] += 1
    total_weight = sum(weights.values())
    for key in weights:
        probabilities[key] = weights[key] / total_weight

# Initial solution setup
warehouse = load_problem()
solver = CheapestPlaceSolver(warehouse, costs_type=CostsType.DECISION)
iterations = 1000
x = 0
solution = []
costs = np.empty(iterations, dtype=int)
pod_location = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
Original_Configuration = np.empty((iterations, 10), dtype=int)
Next_Configuration = np.empty((iterations, 10), dtype=int)
Original_Configuration[x] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Initial solution with cheapest place
while not warehouse.finished():
    place_id, pod, station_id = solver.decide_new_place()
    solution.append(place_id)
    previous_location = pod_location[pod-1]
    Next_Configuration[x] = Original_Configuration[x]
    Next_Configuration[x][previous_location-1] = 0
    Next_Configuration[x][place_id-1] = pod
    pod_location[pod-1] = place_id
    if place_id != 0 and previous_location != 0:
        costs[x] = warehouse.costs.from_station(station_id, place_id) + warehouse.costs.to_station(previous_location, station_id)
    if x != iterations-1:
        Original_Configuration[x+1] = Next_Configuration[x]
    x += 1
    warehouse.next(place_id)

current_best = solution
weights, probabilities = initialize_adaptive_strategy()
methods = list(weights.keys())

n = 0
while n < iterations:
    destroy_method = select_method(probabilities, [m for m in methods if 'destroy' in m])
    repair_method = select_method(probabilities, [m for m in methods if 'repair' in m])
    destroyed_solution = destroy_solution(solution, destroy_method)
    new_solution = repair_solution(destroyed_solution, repair_method)

    new_cost = np.sum(costs)        # Calculate the cost of the new solution (placeholder logic)
    current_cost = np.sum(costs)    # Calculate the cost of the current solution (placeholder logic)

    if new_cost < current_cost:
        if new_cost < np.sum(current_best):
            current_best = new_solution
        solution = new_solution
        success = True
    else:
        success = False

    update_adaptive_strategy(weights, probabilities, destroy_method, success)
    update_adaptive_strategy(weights, probabilities, repair_method, success)
    n += 1

result = current_best

# region print
print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))
print(np.sum(costs))
# Save solution to a JSON file.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)
# endregion
