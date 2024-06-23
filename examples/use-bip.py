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

""" Solve a small test problem exactly with Binary Integer Programming. The test problem contains 10 places, 10 pods,
two stations with queue of the length 3 and 1000 pod departures.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor:: Ruslan Krenzler

17 Juli 2018
"""
import sys
sys.path.append('../')  # noqa: E402
import logging
from prp.solvers.simple import CheapestPlaceSolver, PlaybackSolver
import prp.recorder as recorder
import prp.xy as xy
import prp.stats
import prp.utils as utils
import prp.solvers.bip as bip

LAYOUT_FILE = "../data/10-layout.json"
INITIAL_STATE_FILE = "../data/10-initial-state.json"
COSTS_FILE = "../data/10-costs.json"
DEPARTURES_FILE = "../data/10-departures.json"

# Output file
SOLUTION_FILE = "../data/solutions/10-bip-solution.json"


def load_problem():
    """Load a test system with 10 places and 10 pods randomly distributed among them."""
    layout = xy.Layout()
    with open(LAYOUT_FILE, 'r') as infile:
        layout.load_from_json(infile)
    warehouse = layout.get_empty_warehouse()
    with open(INITIAL_STATE_FILE, 'r') as infile:
        recorder.load_initial_state_from_json(infile, warehouse)
    with open(DEPARTURES_FILE, 'r') as infile:
        departures = recorder.load_departures_from_json(infile)
    warehouse.set_departure_generator(departures)
    costs = layout.get_costs()
    warehouse.set_costs(costs)
    return warehouse


def get_cheapest_place_costs(warehouse):
    """Return costs when using cheapest-place solver with costs from station."""
    warehouse = prp.stats.copy_warehouse(warehouse)
    solver = CheapestPlaceSolver(warehouse, warehouse.costs)

    while not warehouse.finished():
        place_id = solver.decide_new_place()
        warehouse.next(place_id)

    return warehouse.total_costs


warehouse = load_problem()

print("Running BIB solver.")
logging.basicConfig(level=logging.DEBUG)
upper_costs = get_cheapest_place_costs(warehouse)
print("Use upper costs bound {} as an upper costs bound.".format(upper_costs))
(solution, problem) = bip.solve(warehouse, threads=4, costs_upper_bound=upper_costs)

# Save the results.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)

for place_id in solution:
    warehouse.next(place_id)

if not warehouse.finished():
    print("Problem is NOT solved completely")

print("Total costs {c} at time {t}, average costs {avg}".format(c=warehouse.total_costs,
                                                                t=warehouse.t, avg=warehouse.total_costs / warehouse.t))
