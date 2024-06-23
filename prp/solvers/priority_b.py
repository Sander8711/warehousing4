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
"""This module contains the Priority B solvers.

.. moduleauthor: Ruslan Krenzler

27. June 2018.
"""

from collections import namedtuple
import copy
import prp.core.warehouse as warehouse_mod
from prp.core.objects import INVALID_ID
from prp.core.departure_generators import DeterministicDepartures
from prp.solvers.priority_a import DEFAULT_PRIORITY_FACTOR


class KnownData:
    """Simulate partial knowledge about future departures."""

    def __init__(self, departures: DeterministicDepartures, begin_t):
        """Create statistics from known departures.

        :param begin_t: last time when the corresponding pod will be inside the storage area.
           If the system is at time 0 and the current departure is 7 that means begin_t = 0
        """
        self._all_departures = copy.copy(departures.get_all_departures())
        self.begin_t = begin_t

        # Create inital empty pod lists, grouped them by station IDs:
        # Find all available stations.
        station_ids = set()
        for departure in self._all_departures:
            station_ids.add(departure[1])
        self.departures_by_station = {}
        for station_id in station_ids:
            self.departures_by_station[station_id] = []

    def update_data(self, warehouse: warehouse_mod.Warehouse, ndepartures: int):
        """Update station lists."""
        added_departures = 0
        for station_id in self.departures_by_station.keys():
            self.departures_by_station[station_id] = []

        # Now add departures which are currently in the station queue.
        for (station_id, station) in warehouse.stations.items():
            if added_departures >= ndepartures:
                break
            for pod_id in station.state:
                self.departures_by_station[station_id].append(pod_id)
                added_departures += 1

        # Add remaining departures.
        begin_index = warehouse.t - self.begin_t
        end_index = min(begin_index + ndepartures - added_departures, len(self._all_departures))
        try:
            for i in range(begin_index, end_index):
                task = self._all_departures[i]
                self.departures_by_station[task[1]].append(task[0])
        except TypeError:
            print(begin_index)
            print(end_index)


Departure = namedtuple("Departure", ["t", "pod_id", "station_id"])


class FrequencyCounter:
    """Counts how often a some item occurs."""

    def __init__(self, keys):
        # Set event number to 0
        self.counters = dict(zip(keys, len(keys) * [0]))

    def increment(self, key):
        """Increment the count of a pod."""
        self.counters[key] += 1

    def add(self, key, v):
        """Add value v to the count."""
        self.counters[key] += v

    def count(self, key):
        """Return absolute frequency of a pod."""
        return self.counters[key]

    def total(self):
        return sum(self.counters.values())


class Solver:
    """This is Offline Online version of dynamic solver."""

    def __init__(self, warehouse):
        self.warehouse = warehouse
        self.pod_history = FrequencyCounter(warehouse.pods)
        self.pod_future = FrequencyCounter(warehouse.pods)
        self.station_history = FrequencyCounter(warehouse.stations.keys())
        self.station_future = FrequencyCounter(warehouse.stations.keys())
        self.station_dep = {}  # Departures from station relatively to the beginning of the 0-th service.
        self.use_unknown_frequencies = True
        self.priority_factor = DEFAULT_PRIORITY_FACTOR

    def get_service_times(self, current_station):
        """Return estimation of inter-departure times rescaled by sum of the service times."""
        inter_deps = {}
        for station_id in self.warehouse.stations.keys():
            f_current = self.station_history.count(current_station) + self.station_future.count(current_station)
            f_station_id = self.station_history.count(station_id) + self.station_future.count(station_id)
            inter_deps[station_id] = f_current / f_station_id

        return inter_deps

    def update_departures(self, departure_lists):
        self.departure_lists = departure_lists

    def update_statistics(self, current_station):
        # Recalculate future statistics.
        self.pod_future = FrequencyCounter(self.warehouse.pods)
        for (station_id, tasks) in self.departure_lists.items():
            for task in tasks:
                self.pod_future.increment(task)
                self.station_future.increment(station_id)

        # Create departure lists normalized by station statistics and started with 0.
        inter_deps = self.get_service_times(current_station)

        for (station_id, tasks) in self.departure_lists.items():
            self.station_dep[station_id] = []
            t = 0
            for task in tasks:
                self.station_dep[station_id].append(Departure(t=t, pod_id=task, station_id=station_id))
                t += inter_deps[station_id]

    # The same as in A.
    def scale_position(self, places, pods, pod_id):
        """Convert position in pod list into positin in the place list."""
        i = pods.index(pod_id)
        if len(pods) > len(places):
            # Rescale and discritisze.
            i = int(len(places) / len(pods) * i)

        return places[i]

    def get_T(self, current_pod, current_station):
        """Estimate next departure of the current pod from current station.

        The estimaton T can be larger than the actual departure but should not be smaller.
        """
        earlest_station_dep = float("inf")
        next_station_id = None
        for (station_id, departures) in self.station_dep.items():
            for departure in departures:
                # Do not include first departure, check only subsequent departures
                if departure.pod_id == current_pod and 0 < departure.t < earlest_station_dep:
                    earlest_station_dep = departure.t
                    next_station_id = departure.station_id

        inter_deps = self.get_service_times(current_station)
        # If earliest departure is not found just take estimate it
        if next_station_id is None:
            # Estimate how many other pods are on average between two consequtive departures of the current pod
            n_avg_others = (self.pod_history.total() + self.pod_future.total()) / \
                           (self.pod_history.count(current_pod) + self.pod_future.count(current_pod))

            earlest_station_dep = max(len(self.station_dep[current_station]), n_avg_others + 1) * inter_deps[
                current_station]
            next_station_id = current_station

        # Estimate departure time from storage.
        dep_t = earlest_station_dep - self.warehouse.stations[next_station_id].max_n * inter_deps[next_station_id]
        dep_t = max(0.00001, dep_t)  # Remove some inconsistant values in the beginning of the algorithm
        return dep_t

    def estimate_unknown_frequencies(self, current_station, T):
        freq = dict(zip(self.warehouse.pods, [0] * len(self.warehouse.pods)))
        service_times = self.get_service_times(current_station)

        total = self.pod_history.total() + self.pod_future.total()
        for pod_id in self.warehouse.pods:
            num_services = 0
            # Callect all services.
            for (station_id, t) in service_times.items():
                num_services += max(0, T / service_times[station_id] - (len(self.departure_lists[station_id]) - 1))
            # Select portion of the services according to statistics
            freq[pod_id] = num_services * (self.pod_history.count(pod_id) + self.pod_future.count(pod_id)) / total
        return freq

    # Similar to A
    def place_costs(self, from_station_id, to_place, station_weights):
        """Estimate costs of a place by probability of the future stations."""
        result = self.warehouse.costs.from_station(from_station_id, to_place)
        # add to stations
        for (id, w) in station_weights.items():
            result += self.warehouse.costs.to_station(to_place, id) * w
        return result

    # Similar to A, but in addition to historical values it uses future valuese..
    def estimate_station_weights(self):
        """Use saved frequencies to estimate probability for the next station.

        If the algorithm just started, and the frequencies are unknown. Return uniform distribution.
        We ignore current station, which is neither in historical nor in futre data. This is because
        the number is negligible but makes the code more complecate.
        """
        w = {}
        total_frequency = self.station_history.total() + self.station_future.total()
        # Special case when no data is available.
        if total_frequency == 0:
            for station_id in self.warehouse.stations.keys():
                w[station_id] = 1 / len(self.warehouse.stations)
            return w

        for station_id in self.warehouse.stations.keys():
            station_count = self.station_history.count(station_id) + self.station_future.count(station_id)
            w[station_id] = station_count / total_frequency

        return w

    def concurrent_pods(self, current_pod, current_station=None):
        """Return list of pods sorted by priority. Take in account the priority factor."""
        self.update_statistics(current_station)
        PriorityEntry = namedtuple('PriorityEntry', ['pod_id', 'priority'])
        entries = []
        dep_t = self.get_T(current_pod, current_station)
        # First determine earliest departure time from the storage
        # Now add only pods which departs before dep_t
        pod_frequencies = FrequencyCounter(self.warehouse.pods)
        for (station_id, departures) in self.station_dep.items():
            for departure in departures:
                if departure.t < dep_t:
                    pod_frequencies.increment(departure.pod_id)
                # The next line does not bring much.
                # else:
                #    break # We asume that departures are sored by time.

        # add estimated frequences for missing data.
        if self.use_unknown_frequencies:
            f_unkown = self.estimate_unknown_frequencies(current_station, dep_t)
            for (pod_id, f) in f_unkown.items():
                pod_frequencies.add(pod_id, f)
        # Now create a priority from corresponding pod frequecies.
        for (pod_id, abs_freq) in pod_frequencies.counters.items():
            if abs_freq == 0:
                continue  # scip zero entries.
            factor = 1
            if pod_id == current_pod:
                factor = self.priority_factor
            if abs_freq != 0:
                entries.append(PriorityEntry(pod_id=pod_id, priority=abs_freq * factor))
        # Sort pods by priorities. Higher priority are in the front.
        entries = sorted(entries, key=lambda x: x.priority, reverse=True)
        # Return only pod_ids.
        return [x.pod_id for x in entries]

    # This function is the same as in priority A.
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

    def decide_new_place(self):
        """Decide new place."""
        (pod, station_id) = self.warehouse.next_arrival_to_storage()
        # No pod must leave a station, skip it.
        if pod == INVALID_ID:
            return INVALID_ID

        # Ask other pods if they want to have these places.
        # Update frequencies. Do it before calculate priority.
        # Determine index of the place for the new pod.
        pods = self.concurrent_pods(pod, station_id)
        places = self.get_available_places(station_id)
#        pods_old = self.want_to_change(pods, places)
        pods = self.better_want_to_change(pods, places)
        self.pod_history.increment(pod)
        self.station_history.increment(station_id)
        # print("t = {}".format(self.warehouse.t))
        return self.scale_position(places, pods, pod)

    # The same as in A.
    def average_costs(self, place_id):
        """Estimate costs of a place by probability of the future stations."""
        station_weights = self.estimate_station_weights()
        result = 0
        # add to stations
        for (station_id, w) in station_weights.items():
            result += w * (self.warehouse.costs.from_station(station_id, place_id) +
                           self.warehouse.costs.to_station(place_id, station_id))
        return result

    # Estimated costs
    def estimated_costs(self, from_station, place_id, to_station):
        """Estimate costs of a place by probability of the future stations."""
        station_weights = self.estimate_station_weights()
        # add to stations
        result = 0
        if from_station != INVALID_ID:
            result = self.warehouse.costs.from_station(from_station, place_id)
        else:
            for (station_id, w) in station_weights.items():
                result += w * (self.warehouse.costs.from_station(station_id, place_id))

        if to_station != INVALID_ID:
            result += self.warehouse.costs.to_station(place_id, to_station)
        else:
            for (station_id, w) in station_weights.items():
                result += w * (self.warehouse.costs.to_station(place_id, station_id))

        return result

    # Do not forget to change it to a real estimator later.
    def estimate_from_station(self, pod):
        # Use queue information
        for _id, station in self.warehouse.stations.items():
            if pod in station.state:
                return _id

        # Use perfect guess for experimental purpose first.
        self.warehouse.departure_generator.departures
        # find first occurance of the pod.
        for i in range(0, len(self.warehouse.departure_generator)):
            if pod == self.warehouse.departure_generator.departures[i][0]:
                return self.warehouse.departure_generator.departures[i][1]

        return INVALID_ID

    # Do not forget to change it to a real estimator
    def estimate_to_station(self, pod):
        return INVALID_ID  # Switch off.

    def pod_wants_to_change(self, pod, available_places):
        """Return place from available places, where the pod want to move to.

        Return place instead of index, even if the index is computationally more optimal.
        Keep the code understandable.
        """
        # Only remove pods in storage area.
        place_id = self.warehouse.place_by_pod(pod)
        from_station_id = self.estimate_from_station(pod)
        to_station_id = self.estimate_to_station(pod)

        if place_id is None:
            best_costs = float("Inf")
        else:
            best_costs = self.estimated_costs(from_station_id, place_id, to_station_id)

        best_place = INVALID_ID
#        index = 0  # Used for log only
        for place_id in available_places:
            #            avg_costs = self.estimated_costs(INVALID_ID, place_id, INVALID_ID)
            #            avg_costs2 = self.average_costs(place_id)

            other_costs = self.estimated_costs(from_station_id, place_id, to_station_id)
            if other_costs < best_costs:
                best_place = place_id
                best_costs = other_costs
#                best_index = index
#            index += 1

        return best_place

    def better_want_to_change(self, pods, available_places):
        """Return pods sorted by priority how want to have availabe places.

        High priority first.
        """
        available_places = copy.copy(available_places)
        # The next line only required for statistical purpose. It can be removed later
        available_places = sorted(available_places, key=lambda x: self.average_costs(x))
        result = []
        for pod in pods:
            better_place = self.pod_wants_to_change(pod, available_places)
            current_place_id = self.warehouse.place_by_pod(pod)

            if better_place != INVALID_ID:
                # This pod prefers to move to the other place.
                result.append(pod)
                available_places.remove(better_place)
            else:
                # There is special rule for places which have no current place and they must change.
                if current_place_id is None:
                    result.append(pod)

        return result

    # The same as in A. (This part needs to be improved later)
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
