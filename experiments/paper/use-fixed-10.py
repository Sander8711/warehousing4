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

""" Find optimal fixed position for a small test instance with 10 places, 10 pods,
two stations with queue of the length 3 and 1000 pod departures.The departures are from a paper.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2


Note, even if the places in the small 10-place system are already sorted by weights, the real frequency within
1000 steps is only in ca 1/3 cases is sorted as weights. In addition there are some differences, at the end of
the simulation, when some of the places stays in the queue.

.. moduleauthor:: Ruslan Krenzler

12 March 2019
"""

import sys
sys.path.append('../../')  # noqa: E402

import prp.utils as utils
import prp.recorder as recorder
import prp.xy
from prp.solvers.simple import FixedPlaceSolver
import small_problem

# Output paths.
SOLUTION_FILE = "../../data/paper/solutions/10-fixed-place-solution.json"

warehouse = small_problem.load()

print("Calculate fixed solution.")

# Keeps the same position as in the initial state.
# Select fixed point solver, which
solver = FixedPlaceSolver(warehouse)
# Run the system until no departure left. Store solution.
solution = []

while not warehouse.finished():
    place_id = solver.decide_new_place()
    solution.append(place_id)
    warehouse.next(place_id)

print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))
# Save the results.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)