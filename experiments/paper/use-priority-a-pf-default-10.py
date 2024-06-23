# Pod Repositioning Problem
# Copyright (C) 2017, 2018, 2019 Arbeitsgruppe OR an der Leuphana Universität Lüneburg
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

"""
Apply priority A algorithm with an optimal prioritz factor 2.41 between 0.9 and 4.09 to an instance with 10 places,
10 pods, two stations with queue of the length 3, and 1000 pod departures.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor:: Ruslan Krenzler

18 Januar 2019
"""

import sys
sys.path.append('../../')  # noqa: E402

import prp.solvers.priority_a as priority_a
import prp.recorder as recorder
import prp.utils as utils
import small_problem

# Problem settings.
# Output file
SOLUTION_FILE = "../../data/paper/solutions/10-priority-a-pf-default-solution.json"


warehouse = small_problem.load()

print("Calculate solution with Algorithm A")

solver = priority_a.Solver(warehouse)

solver.consider_happy_pods = True
print("Using default priority factor factor {}".format(solver.priority_factor))

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
