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

""" Apply cheapest-place algorithm to a test instance with 10 places, 10 pods, two stations with queue of the length 3
and 1000 pod departures. The departures are from a paper.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor:: Ruslan Krenzler

12 March 2019
"""

import sys
sys.path.append('../../')  # noqa: E402

from prp.solvers.simple import CheapestPlaceSolver, CostsType
import prp.recorder as recorder
import prp.utils as utils
import small_problem

# Output file
SOLUTION_FILE = "../../data/paper/solutions/10-cheapest-place-solution.json"

warehouse = small_problem.load()


print("Use cheapest-place algorithm with full costs (from and to station).")
# Use cheapest place solver. For the costs use full costs of the decision. That means
# costs from the station and costs to the next station.
solver = CheapestPlaceSolver(warehouse, costs_type=CostsType.DECISION)

# Run the system until no departure left. Store solution.
solution = []

while not warehouse.finished():
    place_id = solver.decide_new_place()
    solution.append(place_id)
    warehouse.next(place_id)

print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))

# Save solution to a JSON file.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)

