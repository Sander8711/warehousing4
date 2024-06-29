from prp.solvers.simple import CheapestPlaceSolver, CostsType, RandomSolver
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils
import json
import numpy as np
import prp.core.costs as costs_mod

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

def selectdestroymethod():
    print('placeholder')

def selectrepairmethod():
    print('placeholder')

def generatesolution():
    print('placeholder')

def evaluatesolution(solution):
    tocost = sum(solution)
    fromcost = 0
    data = json.load(DEPARTURES_FILE)
    for sublist in data:
        fromcost += sublist[0]
    totalcost = tocost + fromcost
    return totalcost

def acceptstrategy():
    print('placeholder')

def updateadaptivestrategy():
    print('placeholder')

def updatesuccesrate():
    print('placeholder')

#Adaptive large neighborhood initialization
stopcondition = 1000
n = 1
solutionvalue = evaluatesolution(solution)
currentbest = solution
currentbestvalue = solutionvalue

#Adaptive large neighborhood algorithm
while n < stopcondition:
    #Choose destroy method
    selectdestroymethod()
    #Choose repair method
    selectrepairmethod()
    #Generate new solution
    newsolution = generatesolution()
    newsolutionvalue = evaluatesolution(newsolution)

    if newsolutionvalue < solutionvalue:
        if newsolutionvalue < currentbestvalue:
            currentbest = newsolution
            currentbestvalue = newsolutionvalue
        solution = newsolution
        solutionvalue = newsolutionvalue
    else:
        if acceptstrategy == True:
            solution = newsolution
            solutionvalue = newsolutionvalue
    
    #Update adaptive strategy(weights, probabilities, degree of destruction)
    updateadaptivestrategy
    #Updatesuccesrate(destroymethod, repairmethod)
    updatesuccesrate
    n += 1

result = currentbest

 
#region print
print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))
print(np.sum(costs))
# Save solution to a JSON file.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)
#endregion

