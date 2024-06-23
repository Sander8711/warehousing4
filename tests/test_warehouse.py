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
"""Test objects.

27 June 2018

.. moduleauthor:: Ruslan Krenzler
"""

import unittest
import prp.core.objects as objects
from prp.core.warehouse import Warehouse
import prp.solvers.simple as simple
import prp.core.departure_generators as task_generators

class OneCosts(objects.Costs):
    """Test cost function which return always 1."""

    def from_station(self, station_id: int, place_id: int):
        return 1

    def to_station(self, place_id, station_id):
        return 1


class TestSystem(unittest.TestCase):
    """Test station."""

    def test_simple_system(self):
        system = Warehouse()
        system.set_num_places(10)
        system.set_num_pods(10)
        system.set_costs(OneCosts())
        # Set on every place a pod with the same id.
        for place_id in range(1, 10+1):
            system.assign_pod_to_place(place_id, place_id)

        # Add stations
        station = objects.Station(id=1, n=3)
        system.add_station(station)
        station = objects.Station(id=2, n=3)
        system.add_station(station)

        tasks = task_generators.DeterministicDepartures(
            [(1, 1), (2, 1), (3, 1), (4, 1), (5, 2), (6, 2), (7, 2), (8, 2), (9, 1), (10, 2)])
        system.set_departure_generator(tasks)

        # Add Solver
        solver = simple.PlaybackSolver([0, 0, 0, 3, 0, 0, 0, 8, 9, 10])
        place_id = solver.decide_new_place()
        while system.next(place_id):
            place_id = solver.decide_new_place()

if __name__ == '__main__':
    unittest.main()
