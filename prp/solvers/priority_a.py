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
"""This module contains the Piroirty A solver.

.. moduleauthor: Ruslan Krenzler

27. June 2018.
"""

from collections import namedtuple
import copy
import prp.core.warehouse as warehouse_mod
from prp.core.objects import INVALID_ID

DEFAULT_PRIORITY_FACTOR = 1.00001


class Solver:
    """Decide new place using dynamic tetris algorithm."""

    def __init__(self, warehouse: warehouse_mod.Warehouse):
        self.warehouse = warehouse

        self.station_frequencies = {}
        for station_id in warehouse.stations.keys():
            self.station_frequencies[station_id] = 0

        self.pod_frequencies = {}
        for pod_id in warehouse.pods:
            self.pod_frequencies[pod_id] = 0

        self.priority_factor = DEFAULT_PRIORITY_FACTOR

    def estimate_station_weights(self):
        """Use saved frequencies to estimate probability for the next station.

        If the algorithm just started, and the frequencies are unknown. Return uniform distribution.
        """
        w = {}
        total_frequency = sum(self.station_frequencies.values())

        # Special case when no data is available.
        if total_frequency == 0:
            for station_id in self.warehouse.stations.keys():
                w[station_id] = 1 / len(self.warehouse.stations)
            return w

        for station_id in self.warehouse.stations.keys():
            w[station_id] = self.station_frequencies[station_id] / total_frequency
        return w

    def get_deterministic_station_weights(self, station_id):
        w = {}
        for station_id in self.warehouse.stations.keys():
            w[station_id] = 0
        w[station_id] = 1
        return w

    def place_costs(self, from_station_id, to_place, station_weights):
        """Estimate costs of a place by probability of the future stations."""
        result = self.warehouse.costs.from_station(from_station_id, to_place)
        # add to stations
        for (id, w) in station_weights.items():
            result += self.warehouse.costs.to_station(to_place, id) * w
        return result

    def get_available_places(self, from_station_id, to_station_id=None):
        """Create lists of places sorted by costs. The cheapest costs are in the beginning.

        :param from_station_id: from where the pod goes to the new place.
        :param station_id: where the pod goes to the new place. None (default): means unknown.
        In this case the costs will be estimated from frequencies.
        """
        if to_station_id is None:
            station_w = self.estimate_station_weights()
        else:
            # Set weight of the known station to 1 and all the others to 0.
            station_w = self.get_deterministic_station_weights(to_station_id)

        # Estimate costs for all free places
        CostsEntry = namedtuple('CostsEntry', ['place_id', 'costs'])
        entries = []
        for place_id in self.warehouse.available_places:
            entries.append(CostsEntry(place_id=place_id, costs=self.place_costs(from_station_id, place_id, station_w)))
        # Sort costs. Cheaper costs are in the front.
        entries = sorted(entries, key=lambda x: x.costs)
        return [x.place_id for x in entries]

    def estimate_future_usage(self, pod_id):
        return self.pod_frequencies[pod_id]

    def average_costs(self, place_id):
        """Estimate costs of a place by probability of the future stations."""
        station_weights = self.estimate_station_weights()
        result = 0
        # add to stations
        for (station_id, w) in station_weights.items():
            result += w * (self.warehouse.costs.from_station(station_id, place_id) +
                           self.warehouse.costs.to_station(place_id, station_id))
        return result

    # This is the faster non-recursive version than the recursive version in pseudo-code.
    def want_to_change(self, pods, available_places):
        """Return pods sorted by priority how want to have availabe places.

        High priority first.
        """
        available_places = copy.copy(available_places)
        # Sort places by average costs.
        available_places = sorted(available_places, key=lambda x: self.average_costs(x))
        result = []
        for pod_id in pods:
            # Only remove pods in storage area.
            place_id = self.warehouse.place_by_pod(pod_id)
            if place_id is not None:
                # Check if the pod is happy with its own current place.
                if available_places:
                    if self.average_costs(place_id) > self.average_costs(available_places[0]):
                        # This pod prefers to move to the other place.
                        result.append(pod_id)
                        available_places.pop(0)
            else:   # This pod is in not in the storage area.
                    # Its previous place may be lost that is why it always competes.
                result.append(pod_id)

        return result

    def scale_position(self, places, pods, pod_id):
        """Convert position in pod list into positin in the place list."""
        i = pods.index(pod_id)
        if len(pods) > len(places):
            # Rescale and discritisze.
            i = int(len(places) / len(pods) * i)

        return places[i]

    def decide_new_place(self):
        """Decide new place."""
        (pod, station_id) = self.warehouse.next_arrival_to_storage()
        # No pod must leave a station, skip it.
        if pod == INVALID_ID:
            return INVALID_ID

        # Ask other pods if they want to have these places.
        # Update frequencies. Do it before calculate priority.
        self.pod_frequencies[pod] += 1
        self.station_frequencies[station_id] += 1
        # Determine index of the place for the new pod.
        pods = self.concurrent_pods(pod, station_id)
        places = self.get_available_places(station_id)
        pods = self.want_to_change(pods, places)

        return self.scale_position(places, pods, pod)

    def concurrent_pods(self, current_pod, station=None):
        """Return list of pods sorted by priority. Take in account the priority factor."""
        PriorityEntry = namedtuple('PriorityEntry', ['pod_id', 'priority'])
        entries = []
        for id in self.warehouse.pods:
            factor = 1
            if id == current_pod:
                factor = self.priority_factor
            entries.append(PriorityEntry(pod_id=id, priority=self.estimate_future_usage(id) * factor))
        # Sort pods by priorities. Higher priority are in the front.
        entries = sorted(entries, key=lambda x: x.priority, reverse=True)
        # Return only pod_ids.
        return [x.pod_id for x in entries]
