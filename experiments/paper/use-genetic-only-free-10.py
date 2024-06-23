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

""" Use evolutionary algorithm to solve to a small test instance.
Every genome consists from indices of free place according to some fix order.

The test instance has 10 places, 10 pods, two stations with queue of the length 3 and 1000 pod departures.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor: Ruslan Krenzler

25. March 2019
"""

import sys
sys.path.append('../../')  # noqa: E402

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
import prp.utils as utils
from prp.solvers.simple import CostsType
import prp.solvers.evo_simple as evo_simple
import prp.solvers.evolution_only_free as evo
from prp.solvers.optimal_fixed import get_place_costs
import small_problem

# Output file
SOLUTION_FILE = "../../data/paper/solutions/10-genetic-of-solution.json"

# Set it to None if you do not want to write data to a file.
CSV_FILE = None

# Use normal random instead of numpy.random.seed(7) to get reproducible results.
random.seed(7)
POPULATION_SIZE = 100
MAX_GENERATIONS = 100000
MAX_NO_IMPROVEMENTS = 100


def get_place_ordered_by_avg_costs():
    warehouse = small_problem.load()
    avg_costs = get_place_costs(warehouse)
    places = list(avg_costs.keys())
    return list(sorted(places, key=lambda x: avg_costs[x]))


# Do not use numpy.ndarray. It is slower than list. Use array array with 4byte integer values.
# 2 bytes are fast but it is too small to contain the large maximum value.
#PLACE_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
PLACE_ORDER = get_place_ordered_by_avg_costs()
print("Use place order: {}".format(PLACE_ORDER))

warehouse = small_problem.load()
helper = evo.Helper(warehouse, PLACE_ORDER)

creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", array.array, typecode="l", fitness=creator.FitnessMin)
toolbox = base.Toolbox()
initial_solution = helper.cheapest_place_solution(CostsType.DECISION)
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

# Swich on multiprocessing.
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
print("Best fitness: {}".format(hof[0].fitness))

solution = helper.ordered_to_original(hof[0])
# Save the best individual.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)
