from prp.solvers.simple import CheapestPlaceSolver, CostsType, RandomSolver
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils
import json
import numpy as np
import prp.core.costs as costs_mod
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
        print(costs)
        warehouse.set_costs(costs)
    with open(INITIAL_STATE_FILE, 'r') as infile:
        recorder.load_initial_state_from_json(infile, warehouse)
    with open(DEPARTURES_FILE, 'r') as infile:
        departures = recorder.load_departures_from_json(infile)
        warehouse.set_departure_generator(departures)
    return warehouse

#initial solution
warehouse = load_problem()
#endregion

#select solver
solver = CheapestPlaceSolver(warehouse, costs_type=CostsType.DECISION)
solver2 = RandomSolver(warehouse)

#initialize arrays
iterations = 1000
x=0
solution = []
costs = np.empty(iterations,dtype=int)
pod_location=[1,2,3,4,5,6,7,8,9,10]
Original_Configuration=np.empty((iterations,10),dtype=int)
Next_Configuration = np.empty((iterations,10),dtype=int)
Original_Configuration[x] = [1,2,3,4,5,6,7,8,9,10]

#region initial solution with cheapest place    
while not warehouse.finished():
    place_id,pod,station_id = solver.decide_new_place()
    solution.append(place_id)
    
   #store movements in arrays in order to use in heuristic
    previous_location=pod_location[pod-1]
    Next_Configuration[x]=Original_Configuration[x]
    Next_Configuration[x][previous_location-1]=0
    Next_Configuration[x][place_id-1]=pod
    pod_location[pod-1]=place_id
    
    #can only store costs if a movement is made
    if place_id != 0 and previous_location != 0:
        costs[x]= warehouse.costs.from_station(station_id, place_id)+ warehouse.costs.to_station(previous_location, station_id)
   
    #cannot store configurations in the last iteration
    if x != iterations-1:
        Original_Configuration[x+1]=Next_Configuration[x]
    x+=1
    warehouse.next(place_id)
#endregion

def generateneighborsolution(solution):
    warehouse2 = warehouse
    randomindex = np.random.randint(len(solution))
    newsolution = solution[:randomindex]
    firstpass = True

    x = randomindex 
    while len(newsolution) <= iterations - 1:
        if firstpass == True:
            place_id,pod,station_id = solver2.decide_new_place()
            newsolution.append(place_id)
            #can only store costs if a movement is made
            if place_id != 0 and previous_location != 0:
                costs[x]= warehouse2.costs.from_station(station_id, place_id)+ warehouse2.costs.to_station(previous_location, station_id)

            #cannot store configurations in the last iteration
            if x != iterations-1:
                Original_Configuration[x+1]=Next_Configuration[x]
            x+=1
            warehouse2.next(place_id)
            firstpass = False
        else:
            place_id,pod,station_id = solver.decide_new_place()
            print(place_id, pod, station_id)
            newsolution.append(place_id)

            #can only store costs if a movement is made
            if place_id != 0 and previous_location != 0:
                costs[x]= warehouse2.costs.from_station(station_id, place_id)+ warehouse2.costs.to_station(previous_location, station_id)

            #cannot store configurations in the last iteration
            if x != iterations-1:
                Original_Configuration[x+1]=Next_Configuration[x]
            x+=1
            warehouse2.next(place_id)

    return solution

'''
#Simulated annealing parameters
initial_temperature = 1000
cooling_rate = 0.995
markov_chain_length = 100
min_temp = 1
current_temp = initial_temperature

#Simulated annealing algorithm
while current_temp > min_temp:

    for i in range(markov_chain_length):

        if neighborsolution < currentsolution:

            if neighborsolution < bestsolutionsofar:
                storebestsolution
                bestsolutionsofar = neighborsolution
            else:
                currentsolution = neighborsolution
        
        else:
            r = np.random()
            if r < np.exp((currentsolution - neighborsolution) / current_temp):
                currentsolution = neighborsolution
            else:
                restorebestsolution

    current_temp = current_temp * cooling_rate                
'''
newsolution = generateneighborsolution(solution)
print(solution)
print(newsolution)
 
#region print
print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))
print(np.sum(costs))
# Save solution to a JSON file.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)
#endregion
    