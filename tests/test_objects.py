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
import core.objects as objects


class TestStation(unittest.TestCase):
    """Test station."""

    def test_simple_station(self):
        """Test a simple station with maximally one pod."""
        max_size = 1
        station = objects.Station(1, max_size)
        former_head = station.enqueue(11)
        self.assertEqual(station.state, [11])
        self.assertEqual(former_head, objects.INVALID_ID)
        former_head = station.enqueue(22)
        self.assertEqual(station.state, [22])
        self.assertEqual(former_head, 11)
        self.assertEqual(station.dequeue(), 22)
        self.assertEqual(station.state, [])
        station.enqueue(11)
        station.enqueue(22)
        station.delete_pods()
        self.assertEqual(station.state, [])

    def test_station(self):
        """Test stations with 2 -- 5 pods."""
        for max_n in range(2, 5):
            # Create test pods
            test_pods = []
            for i in range(0, max_n):
                test_pods.append(10 + i + 1)
            station = objects.Station(1, n=max_n)
            for i in range(0, max_n):
                test_pod = test_pods[i]
                former_head = station.enqueue(test_pod)
                self.assertEqual(len(station), i + 1)
                self.assertEqual(former_head, objects.INVALID_ID)
            for i in range(0, max_n):
                pod_must_be = test_pods[i]
                former_head = station.dequeue()
                self.assertEqual(former_head, pod_must_be)

    def test_cost(self):
        costs = objects.ConstantCosts(station_ids=range(1, 3), place_ids=range(1, 11), from_station=5)
        self.assertEqual(costs.from_station(1, 2), 5)
        self.assertEqual(costs.to_station(2, 1), 5)
        costs = objects.ConstantCosts(station_ids=range(1, 3), place_ids=range(1, 11), from_station=6, to_station=7)
        self.assertEqual(costs.from_station(1, 2), 6)
        self.assertEqual(costs.to_station(2, 1), 7)


if __name__ == '__main__':
    unittest.main()
