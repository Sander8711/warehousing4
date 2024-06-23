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

12 March 2019
"""

import sys
sys.path.append('../../')  # noqa: E402

import prp.recorder as recorder
import prp.utils as utils
from prp.solvers.simple import PlaybackSolver, CostsType
import prp.solvers.tetris as tetris
import small_problem


SOLUTION_FILE = "../../data/paper/solutions/10-tetris-solution.json"

warehouse = small_problem.load()

print("Use Tetris algorithm with full decision costs (from and to station) and priority by frequency.")

solution = tetris.solve(warehouse, costs_type=CostsType.DECISION, occ_priority=tetris.OccupationPriority.POD_FREQUENCY)

# Test solution.
solver = PlaybackSolver(solution)

require_decision = True
while require_decision:
    place_id = solver.decide_new_place()
    solution.append(place_id)
    require_decision = warehouse.next(place_id)

print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))

# Save the results.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)
