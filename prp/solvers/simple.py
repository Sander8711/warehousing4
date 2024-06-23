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
"""This module contains simple solvers.

.. moduleauthor: Ruslan Krenzler

27. June 2018.
"""

import math
import random
from enum import Enum
import numpy as np
import prp.core.warehouse as system_mod
from prp.core.objects import INVALID_ID, Costs


class PlaybackSolver:
    """Return previously recorded sequence of actions."""

    def __init__(self, actions):
        self.verbatim = False  # Do not information messages in output.
        self.recorded_actions = actions
        self.current_record_i = 0

    def __len__(self):
        """Return number of *remaining* actions."""
        return len(self.actions - self.current_record_i)

    def reset(self):
        """Start playback recording actions from the beginning."""
        self.current_record_i = 0

    def decide_new_place(self, pod_id: int = None, station_id: int = None):
        """Return recorded action and move to next one."""""
        action = self.recorded_actions[self.current_record_i]
        self.current_record_i += 1
        return action


class CostsType(Enum):
    FROM_STATION_ONLY = 1
#    AVERAGE = 2  # Not yet implemented
#    ESTIMATED = 3  # Not yet implemented.
    DECISION = 4  # Deterministic costs to the storage and from the storage to the next station.


class CheapestPlaceSolver:
    """This solver puts the pod to a most cheapest place."""

    def __init__(self, warehouse, costs: Costs = None, costs_type: CostsType=CostsType.FROM_STATION_ONLY):
        """Send the pod to the cheapest place.

        Without any parameter the function will considered the costs from the station to the storage
        of the warehouse.
        """
        self.warehouse = warehouse
        self.verbatim = False  # Do not information messages in output.
        if costs is None:
            self.costs = warehouse.costs
        else:
            self.costs = costs
        self.costs_type = costs_type

    def decide_new_place(self):
        """Put the pod to the cheapest available place."""
        (pod, station_id) = self.warehouse.next_arrival_to_storage()
        # No pod must leave any station, skip it.
        if pod == INVALID_ID:
            costs_so_far = 0
            return INVALID_ID,pod, station_id

        cheapest_place_so_far = INVALID_ID
        costs_so_far = math.inf
        
        for place_id in self.warehouse.available_places:            
            curr_costs = self.costs.from_station(station_id, place_id)
            if self.costs_type == CostsType.DECISION:
                next_station = self.next_station(pod)
                if next_station != INVALID_ID:
                    curr_costs += self.costs.to_station(place_id, station_id)

            if curr_costs < costs_so_far:
                cheapest_place_so_far = place_id
                costs_so_far = curr_costs
        if self.verbatim:
            print("Pod {} from {} arrives to place {} at {}.".format(
                pod, station_id, cheapest_place_so_far, self.warehouse.t + 1))
        return cheapest_place_so_far, pod, station_id

    def next_station(self, pod_id):
        """Calculate to which station the pod id will go next.

        :return return station id: if the pod will go to some station
        :return INVALID_ID: if the pod will stay in the system.
        """
        for (next_pod, next_station_id) in self.warehouse.departure_generator.departures:
            if next_pod == pod_id:
                return next_station_id
        return INVALID_ID


class SomePlaceSolver:
    """This solver assign a place with smallest index.

    It is used to create temporary solution where places are not important.
    To speed up, this function ignore place which will from which a pod will departure
    in the next step.
    """

    def __init__(self, system: system_mod.Warehouse):
        self.system = system
        self.verbatim = False  # Do not information messages in output.

    def decide_new_place(self, pod: int = None, station_id: int = None):
        (pod, _) = self.system.next_arrival_to_storage()
        if pod != INVALID_ID:
            for place_id in self.system.places:
                # If the place is busy, ignore it.
                if not self.system.place_is_free(place_id):
                    continue

                # Free place found.
                if self.verbatim:
                    print("Pod {} arrives to place {} at {}.".format(pod, place_id, self.system.t + 1))
                return place_id, pod, station_id
            # If the function reaches here, that means the only free place left, is the place of the
            # departing pod.
            (pod, _) = self.system.departure_generator.current()
            return self.system.place_by_pod(pod), pod, station_id
        else:
            return INVALID_ID, pod, station_id

    def no_more_records(self):
        return False


class RandomSolver:
    """This class decides randomly where to put a pod."""

    def __init__(self, system):
        self.system = system

    def decide_new_place(self):
        """Decides **randomly** a new place."""
        (pod, station_id) = self.system.next_arrival_to_storage()
        # No pod must leave any station, skip it.
        if pod == INVALID_ID:
            return INVALID_ID, pod, station_id

        return random.sample(self.system.available_places, 1)[0], pod, station_id


class FixedPlaceSolver:
    """Put pods always to the same places."""

    def __init__(self, warehouse, positions=None):
        """Initalized fixed place solver.

        :param warehouse: The warehouse.
        :param positions: Dictionary pod->place. If it is not defined, the solver will use the current positions of
          the pods. In this case the stations must be empty.
        """
        self.warehouse = warehouse
        self.verbatim = False  # Do not not write information messagees to output.
        if positions is not None:
            self.positions = {}
        else:
            self.fix()

    def fix(self):
        self.positions = {}
        """Make a snapshot of the current storage area and keep the position in the assignment map."""
        for place_id, pod_id in self.warehouse.place_to_pod.items():
            if pod_id is not None:
                self.positions[pod_id] = place_id

    def decide_new_place(self):
        """Put the pod to its old place."""

        (pod, station_id) = self.warehouse.next_arrival_to_storage()
        # No pod must leave any station, skip it.
        if pod == INVALID_ID:
            return INVALID_ID, pod, station_id

        return self.positions[pod], pod, station_id
