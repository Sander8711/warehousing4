from prp.solvers.simple import CheapestPlaceSolver, CostsType, RandomSolver
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils
import json
import numpy as np
import prp.core.costs as costs_mod
import random
import copy
from tqdm import tqdm

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
solver2 = CheapestPlaceSolver(warehouse, costs_type=CostsType.DECISION)
solver = RandomSolver(warehouse)

#initialize arrays
iterations = 1000
x=0
solution = []
costs = np.zeros(iterations,dtype=int)
pod_location=[1,2,3,4,5,6,7,8,9,10]
Original_Configuration=np.zeros((iterations,10),dtype=int)
Next_Configuration = np.zeros((iterations,10),dtype=int)
Original_Configuration[x] = [1,2,3,4,5,6,7,8,9,10]

#region initial solution with cheapest place    
while not warehouse.finished():
    place_id,pod,station_id = solver.decide_new_place()
    solution.append(place_id)
    
   #store movements in arrays in order to use in heuristic
    retrieved_pod = warehouse.departure_generator.departures[0][0]
    previous_location = pod_location[retrieved_pod - 1] 
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
    degree_of_destruction = 10                                                              #Initialize arrays
    randomindex = np.random.randint(len(solution))
    newsolution = solution[:randomindex] + solution[randomindex + degree_of_destruction:]   #Destroy solution
    newcost = list(costs[:randomindex]) + list(costs[randomindex + degree_of_destruction:])
    x = len(newsolution)

    while len(newsolution) < iterations:                                                    #Loop until solution is repaired
        place_id = np.random.randint(1,11)
        pod = np.random.randint(1,11)
        station_id = np.random.randint(1,2)

        if len(newcost) <= x:                                                               #Extend newcost list
            newcost.append(0)

        newsolution.append(place_id)                                                        #Add new place_id to solution list
        newcost[x]= warehouse.costs.from_station(station_id, place_id)+ warehouse.costs.to_station(previous_location, station_id)
        x += 1

    total_new_cost = sum(newcost) 

    return newsolution, total_new_cost                                                      #Return neighbor solution and cost

#Simulated annealing parameters
initial_temperature = 1000                                                                  #Initialize parameters
cooling_rate = 0.995
markov_chain_length = 100
min_temp = 1

current_temp = initial_temperature                                                          #Copy starting solution and cost
current_solution = solution.copy()
current_cost = sum(costs)
bestcostsofar = current_cost
bestsolutionsofar = solution.copy()

progress_bar = tqdm(total=1400, desc="Processing", unit="iteration")                        #Initialize progress bar
iteration = 0

#Simulated annealing algorithm
while current_temp > min_temp:                                                              #Loop until minimum temp is reached
    for i in range(markov_chain_length):
        neighborsolution, neighborcost = generateneighborsolution(current_solution)         #Generate neighbor solution
        if neighborcost < current_cost:
            if neighborcost < bestcostsofar:                                                #Check if neighbor solution is better then current solution
                bestsolutionsofar = neighborsolution.copy()
                bestcostsofar = neighborcost
            else:
                currentsolution = neighborsolution.copy()
                current_cost = neighborcost      
        else:
            r = np.random.rand()
            if r < np.exp((current_cost - neighborcost) / current_temp):                    #Maybe accept even if solution is worse
                currentsolution = neighborsolution.copy()
                current_cost = neighborcost
            else:
                current_solution = bestsolutionsofar.copy()                                 #Restore best solution this far if neighbor was not accepted
                current_cost = bestcostsofar            
    current_temp = current_temp * cooling_rate                                              #Update temperature with cooling rate       
    progress_bar.update(1)
    iteration += 1

resultsolution = bestsolutionsofar.copy()                                                   #Store the result of the simulated annealing 
resultcost = bestcostsofar

 
#region print
print(resultsolution)  
print(resultcost)
#print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))
#print(np.sum(costs))
# Save solution to a JSON file.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)
progress_bar.close()
#endregion