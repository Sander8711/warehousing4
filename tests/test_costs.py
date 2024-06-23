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
"""Test costs.

27 June 2018

.. moduleauthor:: Ruslan Krenzler
"""
import sys
sys.path.append('../src')
import unittest
import core.costs as costs_mod


class TestCosts(unittest.TestCase):
    """Tests costs."""

    def test_cost(self):
        costs = costs_mod.ConstantCosts(station_ids=range(1, 3), place_ids=range(1, 11), from_station=5)
        self.assertEqual(costs.from_station(1, 2), 5)
        self.assertEqual(costs.to_station(2, 1), 5)
        costs = costs_mod.ConstantCosts(station_ids=range(1, 3), place_ids=range(1, 11), from_station=6, to_station=7)
        self.assertEqual(costs.from_station(1, 2), 6)
        self.assertEqual(costs.to_station(2, 1), 7)

    def test_dict_copy(self):
        costs_a = costs_mod.ConstantCosts(station_ids=range(1, 3), place_ids=range(1, 11), from_station=6, to_station=7)
        costs_b = costs_mod.DictCosts(costs_a)
        self.assertListEqual(list(costs_a.station_ids), list(costs_b.station_ids))
        self.assertListEqual(list(costs_a.place_ids), list(costs_b.place_ids))

        for station_id in costs_a.station_ids:
            for place_id in costs_a.place_ids:
                a = costs_a.from_station(station_id, place_id)
                b = costs_b.from_station(station_id, place_id)
                self.assertEqual(a, b)
                a = costs_a.to_station(place_id, station_id)
                b = costs_b.to_station(place_id, station_id)
                self.assertEqual(a, b)

    def test_average_costs(self):
        costs_a = costs_mod.ConstantCosts(station_ids=range(1, 3), place_ids=range(1, 11), from_station=6, to_station=7)
        station_weights = {1: 1 / 2, 2: 1 / 2}
        costs_avg = costs_mod.AverageCosts(costs_a, station_weights)
        costs_avg.from_station(1, 3)
        costs_avg.to_station(3, 1)
        costs_avg.average_mapping[3]
        costs_avg.estimated_mapping[1][3]


if __name__ == '__main__':
    unittest.main()
