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
"""Define costs.

12 Juli 2018

.. moduleauthor:: Ruslan Krenzler
"""
from prp.core.objects import INVALID_ID


class Costs:
    """Calculate different costs of a system."""

    @property
    def station_ids(self):
        """Return all station_id from the costs domain."""
        pass

    @property
    def place_ids(self):
        """Return all places from the costs domain."""
        pass

    def from_station(self, station_id: int, place_id: int):
        """Return costs for moving a pod from a sation to a place in the storage area."""
        pass

    def to_station(self, place_id: int, station_id: int):
        """Return costs for moving a pod from a place in the storage area to a station."""
        pass


class ZeroCosts(Costs):
    """Test cost function always returns 0.

    We use it for test purposes. Of for calculations where costs are not important.
    """

    def from_station(self, station_id: int, place_id: int):
        return 0

    def to_station(self, place_id, station_id):
        return 0


class ConstantCosts(Costs):
    """Test cost function always returns constant for to-station costs and for from-station costs.

    We use it for test purposes.
    """

    def __init__(self, station_ids, place_ids, from_station: float, to_station: float = None) -> float:
        """Set up constant costs.

        :param station_ids: station domain of the function.
        :param place_ids: place domain of the function.
        :param from_station: Constant costs from every station.7
        :param to_station: Constant costs to every station (default equal to from-costs).
        """
        self._station_ids = station_ids
        self._place_ids = place_ids
        self._from_station = from_station
        if to_station is None:
            self._to_station = from_station
        else:
            self._to_station = to_station

    @property
    def station_ids(self):
        return self._station_ids

    @property
    def place_ids(self):
        return self._place_ids

    def from_station(self, station_id: int, place_id: int):
        return self._from_station

    def to_station(self, place_id, station_id):
        return self._to_station


class DictCosts(Costs):
    """Store costs as dictionaries."""

    def __init__(self, other_costs: Costs = None):
        if other_costs is None:
            self.num_stations = 0
            self.num_places = 0
            self.to_station_dict = {}
            self.from_station_dict = {}
        else:
            self.num_stations = len(other_costs.station_ids)
            self.num_places = len(other_costs.place_ids)
            self.to_station_dict = self._create_to_station_mapping(other_costs)
            self.from_station_dict = self._create_from_station_mapping(other_costs)

    @staticmethod
    def _create_from_station_mapping(costs):
        """Create a mapping function from a place to a station.

        It is a Station x Place --> R mapping.
        """

        # Init return value.
        mapping = {}

        for station_id in costs.station_ids:
            station_costs = {}  # costs from station_id to other places
            for place_id in costs.place_ids:
                station_costs[place_id] = costs.from_station(station_id, place_id)
            mapping[station_id] = station_costs
        return mapping

    @staticmethod
    def _create_to_station_mapping(costs):
        """Create a mapping function from a place to a station.

        It is a Place x Station --> R mapping.
        """

        # Init return value.
        mapping = {}

        for place_id in costs.place_ids:
            place_costs = {}  # costs for place_id to different stations
            for station_id in costs.station_ids:
                place_costs[station_id] = costs.to_station(place_id, station_id)
            mapping[place_id] = place_costs

        return mapping

    @property
    def station_ids(self):
        return range(1, self.num_stations + 1)

    @property
    def place_ids(self):
        return range(1, self.num_places + 1)

    def from_station(self, station_id: int, place_id: int):
        return self.from_station_dict[station_id][place_id]

    def to_station(self, place_id, station_id):
        return self.to_station_dict[place_id][station_id]

    def set_num_stations(self, n: int):
        """Set number of stations in the costs functions.

        Call this function before setting the costs.
        """
        # Add missing stations to to_station function
        # if n is larger than current number of stations.
        for station_id in range(self.num_stations + 1, n + 1):
            self.from_station_dict[station_id] = {}

        # Remove too large station_id if N is smaller than the previous N
        for station_id in range(n + 1, self.num_stations + 1):
            del self.to_station_dict[station_id]

        self.num_stations = n

    def set_num_places(self, n: int):
        """Set number of places in the costs functions.

        Call this function before setting the costs.
        """
        # Add missing places to to_station function
        # if n is larger than current number of places.
        for place_id in range(self.num_places + 1, n + 1):
            self.to_station_dict[place_id] = {}

        # Remove too large point_id if N is smaller than the previous N
        for place_id in range(n + 1, self.num_places + 1):
            del self.to_station_dict[place_id]

        self.num_places = n

    def set_from_station(self, station_id: int, place_id: int, costs: float):
        self.from_station_dict[station_id][place_id] = costs

    def set_to_station(self, place_id, station_id, costs: float):
        self.to_station_dict[place_id][station_id] = costs


class AverageCosts(DictCosts):
    def __init__(self, costs, weights=None):
        """Calculate various average costs from other costs.

        :param costs: Used to calculate the costs.
        :param weights: station weights, statistical or known. It must be a dictionary station_id -> value
        """
        super(AverageCosts, self).__init__(costs)
        self.orgn_cost = costs
        self.station_weights = weights
        if weights is not None:
            self.average_mapping = self._create_average_mapping()
            self.estimated_mapping = self._create_estimated_mapping()
        else:
            self.average_mapping = None
            self.estimated_mapping = None

    def _create_average_mapping(self):
        mapping = {}
        for place_id in self.place_ids:
            c = 0
            for (station_id, w) in self.station_weights.items():
                c += w * (self.from_station_dict[station_id][place_id] + self.to_station_dict[place_id][station_id])
            mapping[place_id] = c
        return mapping

    def _create_estimated_mapping(self):
        mapping = {}
        for from_station_id in self.station_ids:
            mapping[from_station_id] = {}
            for place_id in self.place_ids:
                c = self.from_station_dict[from_station_id][place_id]
                for (to_station_id, w) in self.station_weights.items():
                    c += w * self.to_station_dict[place_id][to_station_id]
                mapping[from_station_id][place_id] = c
        return mapping

    def deterministic(self, from_station_id, place_id, to_station_id):
        c = self._from_station[from_station_id][place_id]
        if to_station_id != INVALID_ID:
            c += self._to_station[place_id][to_station_id]

        return c
