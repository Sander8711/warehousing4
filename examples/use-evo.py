# Pod Repositioning Problem
# Copyright (C) 2017, 2018 Arbeitsgruppe OR an der Leuphana Universität Lüneburg
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Use evolutionary algorithm to solve to a test instance with 10 places, 10 pods,
two stations with queue of the length 3 and 1000 pod departures.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor: Ruslan Krenzler

18 July 2018
"""

import sys
sys.path.append('../')  # noqa: E402

import copy
import random  # For seed.
import array
import csv
import multiprocessing
import numpy
from deap import base
from deap import creator
from deap import tools
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils

import prp.solvers.evolution as evo
import prp.solvers.evo_simple as evo_simple


# Input files
LAYOUT_FILE = "../data/10-layout.json"
INITIAL_STATE_FILE = "../data/10-initial-state.json"
DEPARTURES_FILE = "../data/10-departures.json"

# Output files:
SOLUTION_FILE = "../data/solutions/10-evo-solution.json"
# Set to None if you do not want a CSV file.
CSV_FILE = "../data/evo-intermediate-from-rnd-results.csv"

random.seed(7)
POPULATION_SIZE = 100
MAX_GENERATIONS = 100000
MAX_NO_IMPROVEMENTS = 100


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


warehouse = load_problem()
helper = evo.Helper(warehouse)

creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", array.array, typecode="L", fitness=creator.FitnessMin)
toolbox = base.Toolbox()
initial_solution = helper.random_solution()
toolbox.register("initialSolution", copy.deepcopy, initial_solution)
toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.initialSolution)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", tools.mutUniformInt, low=helper.min_action(),
                 up=helper.max_action(), indpb=3.0 / len(initial_solution))
toolbox.register("evaluate", helper.evaluate)
toolbox.register("select", tools.selTournament, tournsize=3)

print("Initial solution:")
ind1 = toolbox.individual()
print(ind1)
print("Initial fitness: {}".format(helper.evaluate(initial_solution)))

# Switch on multiprocessing. If you use call statistics in a profiler, switch of multiprocessing-
pool = multiprocessing.Pool()
toolbox.register("map", pool.map)

# Solve.
pop = toolbox.population(n=POPULATION_SIZE)
hof = tools.HallOfFame(1)
stats = tools.Statistics(lambda ind: ind.fitness.values)
stats.register("Avg", numpy.mean)
stats.register("Std", numpy.std)
stats.register("Min", numpy.min)
T = len(initial_solution)
stats.register("MinTotal", lambda x: numpy.min(x) * T)  # Minimal total costs and not average.
stats.register("Max", numpy.max)
helper.reset_counters()
pop, logbook = evo_simple.eaSimple(pop, toolbox, cxpb=0.5, mutpb=0.2, ngen=MAX_GENERATIONS,
                                   maxnoimprovments=MAX_NO_IMPROVEMENTS,
                                   stats=stats, halloffame=hof, verbose=True)

if CSV_FILE is not None:
    with open(CSV_FILE, 'w+') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=logbook.header)
        writer.writeheader()
        writer.writerows(logbook[0:len(logbook)])
        csvfile.close()

print(hof)
print(hof[0].fitness.valid)
print(hof[0].fitness)

# Save the best individual.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(hof[0].tolist(), outfile)
