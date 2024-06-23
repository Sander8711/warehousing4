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

12 March 2019
"""
import sys
sys.path.append('../../')  # noqa: E402

import prp.recorder as recorder
import prp.utils as utils
import prp.solvers.bip_gurobi as bip
import small_problem

# Output file
SOLUTION_FILE = "../../data/paper/solutions/10-bip-gurobi-solution.json"


warehouse = small_problem.load()
print("Running Gurobi BIP solver.")
(solution, model) = bip.solve(warehouse)

# Save the results.
utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)

# Test results
for place_id in solution:
    warehouse.next(place_id)

if not warehouse.finished():
    print("Problem is NOT solved completely")

print("Total costs {c} at time {t}, average costs {avg}".format(c=warehouse.total_costs,
                                                                t=warehouse.t, avg=warehouse.total_costs / warehouse.t))
