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
""" Define departure generators.

.. moduleauthor:: Ruslan Krenzler

29 December 2017


"""
import copy
import numpy
import logging
import math
from prp.core.warehouse import DepartureGenerator, Warehouse
from prp.core.objects import INVALID_ID


def seed(seed):
    numpy.random.seed(seed)


class DeterministicDepartures(DepartureGenerator):
    """Generate departures according to a departure lists."""

    def __init__(self, departures):
        if type(departures) is DeterministicDepartures:
            self.departures = copy.deepcopy(departures.departures)
        else:
            self.departures = departures

    def get_all_departures(self):
        """Return a list of all departures as a list of tupples (time, pod_id, station_id)."""
        return self.departures

    def next(self):
        if len(self.departures) > 0:
            self.departures.pop(0)

    def current(self):
        return self.departures[0]

    def __len__(self):
        return len(self.departures)

    def is_finite(self):
        return True


class MarkovianGenerator(DepartureGenerator):
    """Generate departures according to Markovian description of the problem."""

    def __init__(self, warehouse: Warehouse,
                 w_pods: dict, w_station: dict, n=float("-inf")):
        """Init departure generator with geometricly distributed weights.

        :param p: the weights are then w[i+1] = w[i]*(1-self.p).
        :param n: is maximal number of generated departures.
        """
        self.warehouse = warehouse
        self.pod_weights = w_pods
        self.station_weights = w_station
        self.verbose = False
        self.departures_remains = n
        self.current_departure = None

    def next(self):
        self.current_departure = self._generate()
        self.departures_remains -= 1
        return self.current_departure

    def _get_departure_candidates(self):
        """Return sorted list of pods which may departure.

        The old implementation did not sort this list, that is why the pseudo randomly generated departures
        depended on the solver. To prevent this problem and to make the pseudo random departures independent from the
        solver, we sort the list of pods.
        """
        pods = []
        for (place_id, pod_id) in self.warehouse.place_to_pod.items():
            if pod_id is not INVALID_ID:
                pods.append(pod_id)
        return sorted(pods)

    def _generate(self):
        """Generate new departure."""
        # Check what ids are available in the storage area.
        # Available -- means here that the pod is in the storage area
        # and not at a station.
        pods = self._get_departure_candidates()
        weights = []  # Probability weights of the pods to departure.
        total_w = 0.0

        pods = self._get_departure_candidates()

        for pod_id in pods:
            w = self.pod_weights[pod_id]
            weights.append(w)
            total_w += w

        # Print some debug infomration.
        if self.verbose:
            s = "Available pods:"
            for id in pods:
                s = s + " " + str(id) + ", "

        # Normalize weights.
        for i in range(0, len(weights)):
            weights[i] /= total_w

        pod_id = numpy.random.choice(pods, None, True, weights)
        if self.verbose:
            s = s + " selected {}.".format(pod_id)

        # randomly select a station.
        station_id = numpy.random.choice(list(self.warehouse.stations.keys()), None,
                                         True, list(self.station_weights.values()))
        if self.verbose:
            s = s + " for station {}.".format(station_id)
            s = s + " at time {}+1".format(self.warehouse.t)
            logging.debug(s)
        # Convert pod_id and station_id to int. Otherwise there could
        # be later problems to store int64 with json.
        return int(pod_id), int(station_id)

    def current(self):
        if self.current_departure is None:
            self.current_departure = self._generate()

        return self.current_departure

    def __len__(self):
        return self.departures_remains

    def is_finite(self):
        return self.departures_remains < math.inf


def get_geometric_weights(npods, max_weight_ratio):
    """Calculate weights of the pods, according to a truncating geometric distribution.

    :param npods: Number of pods in the warehouse.
    :param max_weight_ratio: (maximal weight)/(minimal weight).
    """
    w = {}
    # If max_weight_ratio is 1 then we have a limmiting case geometric->unfirom.
    # To prevent problems (device by zero) in subsequent formulas, return uniform distribution directly.
    if max_weight_ratio == 1:
        for pod in range(1, npods + 1):
            w[pod] = 1/npods
        return w

    # Calculate parameter q in such a way that the very rare pod will be max_weight_ratio less frequent as
    # the first one. It holds
    # max_weight_ratio = P(ID = 1)/P(ID = NPODS)
    # P(ID=h)= q^(h-1)*(1-q)/(1-q^NPODS)
    q = max_weight_ratio**(-1 / (npods - 1))  # Not normalized weight of the pod 1.
    w1 = (1 - q) / (1 - q**npods)  # Normalization constant.

    for pod in range(1, npods + 1):
        w[pod] = w1 * q**(pod - 1)

    return w


class UniformGenerator(MarkovianGenerator):
    """Select a pod for the next departure with equal probability."""

    def __init__(self, station_weights, warehouse: Warehouse, n=float("-inf")):
        """Init departure generator with geometricly distributed weights.

        :param station_weights: the weights are then w[i+1] = w[i]*(1-self.p).
        :param n: is maximal number of generated departures.
        """
        pod_weights = self.create_weights(warehouse)
        super(UniformGenerator, self).__init__(pod_weights, station_weights, warehouse, n=n)

    @classmethod
    def create_weights(cls, warehouse):
        n = len(warehouse.place_to_pod)
        weights = dict(zip(warehouse.place_to_pod.keys(), n * [1 / n]))
        return weights


class CyclicGenerator(DepartureGenerator):
    """Randomly select pods without much repeating or missinge some pod.

    The stations are selected independent randomly according to their weights.
    """

    def __init__(self, station_weights, warehouse: Warehouse, n=float("-inf")):
        self.warehouse = warehouse
        self.station_weights = station_weights
        self.verbose = False
        self.departures_remain = n
        self.current_departure = None
        self.current_pod_i = 0
        self.pods = list(sorted(warehouse.pods))
        self.random_shuffle = False
        self.remaining_pods = []
        self.repeat = []

    def _get_pod_list(self):
        if self.random_shuffle:
            return list(numpy.random.choice(self.warehouse.pods, len(self.warehouse.pods), replace=False))
        else:
            return copy.copy(self.pods)

    def next(self):
        self.current_departure = self._generate()
        self.departures_remain -= 1
        return self.current_departure

    def _generate(self):
        """Generate new departure."""
        s = ""
        # If repeating list ist îs not empty try to select pod from it first.
        pod_id = None
        for i in range(0, len(self.repeat)):
            candidate_pod_id = self.repeat[i]
            # Check if the the pod is in the storage
            if self.warehouse.place_by_pod(candidate_pod_id) is not None:
                pod_id = candidate_pod_id
                del self.repeat[i]
                if self.verbose:
                    print("Select again pod {}.".format(pod_id))
                break
        # If no pod were selected from repeat list. Select a pod.
        while pod_id is None:
            if not self.remaining_pods:
                self.remaining_pods = self._get_pod_list()
            candidate_pod_id = self.remaining_pods.pop(0)
            # Check if the the pod is in the storage.
            # If in the storage, this will be our departure pod.
            # If it is in the storage, append it to a repeat least
            # and repeat the cycle.
            if self.warehouse.place_by_pod(candidate_pod_id) is not None:
                pod_id = candidate_pod_id
                break
            else:
                if self.verbose:
                    print("Repeat pod {} later.".format(pod_id))
                self.repeat.append(candidate_pod_id)

        if self.verbose:
            s = s + " selected pod {}.".format(pod_id)

        # randomly select a station.
        station_id = numpy.random.choice(list(self.warehouse.stations.keys()), None,
                                         True, list(self.station_weights.values()))
        if self.verbose:
            s = s + " for station {}.".format(station_id)
            s = s + " at time {}+1".format(self.warehouse.t)
            print(s)
        # Convert pod_id and station_id to int. Otherwise there could
        # be later problems to store int64 with json.
        return int(pod_id), int(station_id)

    def current(self):
        if self.current_departure is None:
            self.current_departure = self._generate()

        return self.current_departure

    def __len__(self):
        return self.departures_remain

    def is_finite(self):
        return self.departures_remain < math.inf
