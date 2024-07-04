import numpy as np
import random
import math
import matplotlib.pyplot as plt
from tqdm import tqdm
from prp.solvers.simple import CheapestPlaceSolver, SomePlaceSolver, CostsType, RandomSolver
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils
import json
import prp.core.costs as costs_mod
from prp.core.objects import INVALID_ID  # Import INVALID_ID from prp.core.objects

# Set directories
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

def generate_neighbor_solution(solution, warehouse, solver_improvement):
    """Generate a neighbor solution by using CheapestPlaceSolver for improvement."""
    # Create a new instance of the warehouse and set its state to match the original warehouse up to random_index
    warehouse2 = load_problem()

    random_index = np.random.randint(len(solution))
    
    # Manually move the pods in warehouse2 to match the state of warehouse up to random_index
    for i in range(random_index):
        place_id = solution[i]
        for pod_id in warehouse.pods:
            if warehouse.place_by_pod(pod_id) == place_id:
                try:
                    warehouse2.assign_pod_to_place(pod_id, place_id)
                except PlaceNotEmpty:
                    print(f"[ERROR] place {place_id} is not empty in the new warehouse instance.")
                break
    
    firstpass = True
    new_costs = np.empty(len(solution), dtype=int)
    previous_location = INVALID_ID  # Initialize previous_location
    
    x = random_index 
    new_solution = solution[:random_index]  # Start the new solution from the random index
    
    while not warehouse2.finished() and len(new_solution) < len(solution):
        if firstpass:
            place_id, pod, station_id = solver_improvement.decide_new_place()
            firstpass = False
        else:
            place_id, pod, station_id = solver_improvement.decide_new_place()
        
        new_solution.append(place_id)
        # Store movements in arrays in order to use in heuristic
        if x < len(solution):  # Ensure x is within bounds
            new_costs[x] = warehouse2.costs.from_station(station_id, place_id) + warehouse2.costs.to_station(previous_location, station_id)
        
        previous_location = place_id  # Update previous_location
        x += 1
        warehouse2.next(place_id)
    
    new_costs_sum = np.sum(new_costs)
    return new_solution, new_costs_sum

# Load warehouse and initialize solvers
warehouse = load_problem()
solver_initial = CheapestPlaceSolver(warehouse, costs_type=CostsType.DECISION)
solver_improvement = CheapestPlaceSolver(warehouse, costs_type=CostsType.DECISION)

# Initialize tqdm for progress bar
pbar = tqdm(total=100)

# Initialize arrays for initial solution
iterations = 1000
x = 0
solution = []
costs = np.empty(iterations, dtype=int)
pod_location = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
Original_Configuration = np.empty((iterations, 10), dtype=int)
Next_Configuration = np.empty((iterations, 10), dtype=int)
Original_Configuration[x] = pod_location[x]  # Initial configuration is the starting pod locations

# region initial solution with cheapest place    
while not warehouse.finished():
    place_id, pod, station_id = solver_initial.decide_new_place()
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

# Simulated annealing parameters
initial_temperature = 1000
cooling_rate = 0.95
markov_chain_length = 100
min_temp = 1
current_temp = initial_temperature

# Simulated annealing algorithm
best_solution = solution.copy()
best_cost = np.sum(costs)
current_solution = solution.copy()
current_cost = best_cost

while current_temp > min_temp:
    for i in range(markov_chain_length):
        neighbor_solution, neighbor_cost = generate_neighbor_solution(current_solution, warehouse, solver_improvement)
        
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
print("Initial total cost:", np.sum(costs))
print("Optimized total cost:", best_cost)

# Save solution to a JSON file.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(best_solution, outfile)

pbar.close()
