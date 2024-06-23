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

"""Create a test instance with 10 places, 10 pods, two stations with queues of the length 3 and 1000 pod departures.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor:: Ruslan Krenzler

16 October 2018
"""
import sys
sys.path.append('../')  # noqa: E402
import math
import prp.recorder as recorder
from prp.core.warehouse import Warehouse
import prp.xy as xy
import prp.utils
from prp.core.objects import INVALID_ID


def load_problem():
    """Load a test system with 10 places and 10 pods randomly distributed among them."""
    layout = xy.Layout()
    with open("../data/10-layout.json", 'r') as infile:
        layout.load_from_json(infile)
        warehouse = layout.get_empty_warehouse()
        costs = layout.get_costs()
        warehouse.set_costs(costs)
    with open("../data/10-initial-state.json", 'r') as infile:
        recorder.load_initial_state_from_json(infile, warehouse)
    with open("../data/10-departures.json", 'r') as infile:
        departures = recorder.load_departures_from_json(infile)
        warehouse.set_departure_generator(departures)
    return warehouse


class MySolver:
    """This solver puts the pod to a most cheapest place."""

    def __init__(self, warehouse: Warehouse):
        self.warehouse = warehouse

    def decide_new_place(self):
        """Put the pod to the cheapest available place."""
        (pod, station_id) = self.warehouse.next_arrival_to_storage()

        # No pod will leave the picking station in next step. Do not assign any place.
        if pod == INVALID_ID:
            return INVALID_ID

        cheapest_place_so_far = INVALID_ID
        costs_so_far = math.inf
        for place_id in self.warehouse.available_places:
            curr_costs = self.warehouse.costs.from_station(station_id, place_id)
            if curr_costs < costs_so_far:
                cheapest_place_so_far = place_id
                costs_so_far = curr_costs

        print("Pod {} from {} arrives to place {} at t {}.".format(
            pod, station_id, cheapest_place_so_far, self.warehouse.t + 1))

        return cheapest_place_so_far


warehouse = load_problem()
solver = MySolver(warehouse)

# Store solution.
solution = []

while not warehouse.finished():
    place_id = solver.decide_new_place()
    solution.append(place_id)
    warehouse.next(place_id)

print("Total costs: {} at time {}.".format(warehouse.total_costs, warehouse.t))

SOLUTION_FILE = "../data/solutions/10-cheapest-place-solution.json"
prp.utils.create_missing_directories_of_file(SOLUTION_FILE)
with open(SOLUTION_FILE, 'w') as outfile:
    recorder.store_solution_to_json(solution, outfile)

