import numpy as np
def constructinitialsolution():
    print()

def generateneighbor():
    print()

def initializeadaptivestrategy():  
    print()

def selectdestroymethod():  
    print()

def selectrepairmethod():  
    print()

def repairsolution():  
    print()

def destroysolution():
    print()

def updateadaptivestrategy():
    print()

def updatesuccesrate():
    print()

e =1
weights = 1
probabiilities = 1
degreeofdestruction = 1
stoppingcreteria = 1
adaptivestrategy = 1
omega = 1
acceptstrategy = 1

#Simulated anealing pseudo code
starttemp =1000                                                                             #initialization
coolingrate = 0.99
markovchainlength = 100
endtemperature = 1

temp = starttemp
solution = constructinitialsolution()                                                       #Initail solution 
currentbest = solution

while not temp < endtemperature:                                                            #Loop that runs until end temperature is reached
    for m in range(1, markovchainlength):                                                   #Loop over the markov chain length
        neighborsolution = generateneighbor(solution)                                       #Generate neighbor solution
        if neighborsolution < solution:                                                     #Accept if neighbor solution is better
            if neighborsolution < currentbest:                                              #Make new best if neighbor solution is better then current best
                currentbest = neighborsolution
            solution = neighborsolution
        else:                                                                               #Else the solution can still be accepted with a 
            if np.random() <= e^((solution - neighborsolution)/ temp):                      #decreasing probability
                solution = neighborsolution
    temp = coolingrate * temp                                                               #Update the temp with the cooling rate

result = currentbest                                                                        #The result is the currentbest solution once 
                                                                                            #the temp is reached.

#Variable large neighborhood search  
solution = constructinitialsolution()                                                       #Construct an initial solution
currentbest = solution
initializeadaptivestrategy(weights, probabiilities, degreeofdestruction)                    #Choose a strategy

while not stoppingcreteria:                                                                 #Run until the stopping criteria is met
    destroymethod = selectdestroymethod(adaptivestrategy, omega)                            #Select a destroy method to use for this loop
    repairmethod = selectrepairmethod(adaptivestrategy, omega(destroymethod))               #Select a repair method to use for this loop
    newsolution = repairsolution(destroysolution(solution, destroymethod), repairmethod)    #Destroy and repair the solution with chosen methods

    if newsolution < solution:                                                              #Check if new solution is better then current
        if newsolution < currentbest:                                                       #Check if new solution is better then best
            currentbest = newsolution
        solution = newsolution
    else:
        if acceptstrategy == True:                                                          #Accept with probability
            solution = newsolution

    updateadaptivestrategy(weights, probabiilities, degreeofdestruction)                    #Update the used methods
    updatesuccesrate(destroymethod, repairmethod)                                           #Update the succes rate of the used methods

result = currentbest                                                                        #The result is the currentbest solution once 
                                                                                            #the stopping criterium is met.
    
    