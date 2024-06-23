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

""" Use tetris algorithm based on frequencies to solve to a small test instance.

The test instance has 10 places, 10 pods, two stations with queue of the length 3 and 1000 pod departures.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor: Ruslan Krenzler

18. July 2018
"""

import sys
sys.path.append('../')  # noqa: E402

import logging

import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils
from prp.solvers.simple import CostsType
import prp.solvers.tetris as tetris

# Input files.
LAYOUT_FILE = "../data/10-layout.json"
INITIAL_STATE_FILE = "../data/10-initial-state.json"
DEPARTURES_FILE = "../data/10-departures.json"

# Set it to None if you do not want to write data to a file.
SOLUTION_FILE = "../data/solutions/10-testris-solution.json"


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

# Switch on logging.
logging.basicConfig(level=logging.INFO)

print("Use Tetris algorithm with full decision costs (from and to station) and priority by frequency.")

solution = tetris.solve(warehouse, costs_type=CostsType.DECISION, occ_priority=tetris.OccupationPriority.POD_FREQUENCY)

# Test solution.
for place_id in solution:
    require_decision = warehouse.next(place_id)

if not warehouse.finished():
    print("Problem is not solved completely!")

print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))

# Save the results.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)
