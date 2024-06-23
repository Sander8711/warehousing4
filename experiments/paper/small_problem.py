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

""" Load a small problem with 10 places, 10 pods, two stations with queue of the length 3
and 1000 pod departures. The departures are from a paper.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor:: Ruslan Krenzler

17 Juli 2018
"""

import prp.recorder as recorder
import prp.xy as xy

# Input files
LAYOUT_FILE = "../../data/10-layout.json"
INITIAL_STATE_FILE = "../../data/10-initial-state.json"
DEPARTURES_FILE = "../../data/paper/10-departures.json"


def load():
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


def evaluate_solution(solution):
    """Evaluate solution of a small test system."""
    warehouse = load()
    # Test results
    for place_id in solution:
        warehouse.next(place_id)

    if not warehouse.finished():
        print("Problem is NOT solved completely")
        return None
    return {"Costs": warehouse.total_costs, "T": warehouse.t}


def evaluate_solution_file(filename):
    """Evaluate solution stored in a JSON file."""
    solution = recorder.load_solution_from_json(filename)
    res = evaluate_solution(solution)
    res["Solution"] = solution
    return res
