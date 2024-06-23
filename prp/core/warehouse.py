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
"""Define essential dynamics of the pod-storage-assignment simulation.

.. moduleauthor:: Ruslan Krenzler

21 November 2017

This module provides core dynamics of the pod-repositioning-problem.
"""

from copy import deepcopy
from prp.core.objects import Station, INVALID_ID, Costs
import logging

class PlaceDoesNotExist(Exception):
    """This exception indicates that a place with particular id does not exist."""

    def __init__(self, message: str, place_id):
        """Set id of the not existing place."""
        self.message = message
        self.id = place_id

    def __str__(self):
        return "[ERROR] place {} does not exist. {}".format(self.id, str(self.message))


class StationDoesNotExist(Exception):
    """This exception indicates that a station with particular id does not exist."""

    def __init__(self, message: str, station_id):
        """Set id of the not existing place."""
        self.message = message
        self.id = station_id

    def __str__(self):
        return "[ERROR] station {} does not exist. {}".format(self.id, str(self.message))


class PodDoesNotExist(Exception):
    """This exception indicates that a pod with particular id does not exist."""

    def __init__(self, message: str, pod_id):
        """Set id of the not existing pod."""
        self.message = message
        self.id = pod_id

    def __str__(self):
        return "[ERROR] pod {} does not exist. {}".format(self.id, str(self.message))


class PodNotInStorage(Exception):
    """This exception indicates that a pod with particular id does not exist."""

    def __init__(self, message: str, pod_id):
        """Set id of the not existing pod."""
        self.message = message
        self.id = pod_id

    def __str__(self):
        return "[ERROR] pod {} is not in storage. {}".format(self.id, str(self.message))



class PlaceNotEmpty(Exception):
    """Place with particular id is not empty."""

    def __init__(self, message: str, place_id):
        """Set id of the not existing place."""
        self.message = message
        self.id = place_id

    def __str__(self):
        return "[ERROR] place {} is not empty. {}".format(self.id, str(self.message))


class PodLocationNotUnique(Exception):
    """A pod was assigned to multiple places."""

    def __init__(self, message: str, pod_id):
        """ Set id of the not existing place."""
        self.message = message
        self.id = pod_id

    def __str__(self):
        return "[ERROR] location of pod {} is not unique.{}".format(self.id, str(self.message))


class NotFound(Exception):
    """Some object (pod, place, station) was not found."""

    def __init__(self, message: str):
        """ Set id of the not existing place"""
        self.message = message

    def __str__(self):
        return "[ERROR] Not found. {}".format(self.message)


class Inconsistency(Exception):
    """Algorithm reached a state which must not exist."""

    def __init__(self, message: str):
        """Set id of the not existing place."""
        self.message = message

    def __str__(self):
        return "[ERROR] Unexpected algorithm state. {}".format(self.message)


class DepartureGenerator:
    """This asks the warehouse to put a particular pod to a particular station."""

    def next(self):
        """Generate next tasks.

        It must return a tuple (pod_id, station_id).
        The warehouse will move the corresponding pod to corresponding station in the next step.
        If the warehouse does not want to move any pod to a station then it must return (0,0).
        """
        pass

    def current(self):
        """Return current task."""
        pass

    def __len__(self):
        """Return total number of remaining tasks including the current tasks.

        It must return float('inf') it there are infirint number of tasks.
        """
        pass

    def is_finite(self):
        """Return true if the generator is finite."""
        return len(self) < float("inf")


class MMapping(dict):
    """This class creates a mapping from domain X to image domain Y.

    This class makes easier to get the inverse image of a value.
    It is basically a python dictionary key->value with inverse function
    value->keys.

    TODO:

    * Find a better name.
    """

    def get_inverse(self, y):
        """Return a set of x such that f(x)=y. Possible I will change it to a list later."""
        ret = set()
        for (curr_x, curr_y) in self.items():
            if curr_y == y:
                ret.add(curr_x)
        return ret


class Warehouse:
    """Mathematical model of a warehouse.

    **Usage**

    Use following steps to setup a warehouse:

    #. Add station with :meth:`add_output_station`.
    #. Set number of places with :meth:`set_num_places`.
    #. Set number of pods with :meth:`set_num_pods`.
    #. Add pods to places or to stations with :meth:`assign_pod_to_place`
       and :meth:`assign_pod_to_station` respectively. The pods and station
       must already exist in the warehouse.
    #. Implement a task generator of type :class:`TaskGenerator`
       and it with :meth:`set_task_generator`.
    #. (Optionally) Implement a solver of type type :class:`Solver`
    #. Finally you can change the state of the warehouse using multiple calls to
       :meth:`next(place)`. Where place is the new place where current pod must move in the next step.
    """

    class MathematicalState:
        """This is mathematical representation of the warehouse problem.

        It consists of place -> pod mapping. It implicitly includes
        the set of all places. Places, which exists but do not point to pods,
        point to 0.
        This mapping is partially injective: Two places are not allowed to
        point to the same pod. Bud it is possible that multiple places points
        to 0.

        It also consist of the station-id -> station-state content mapping.

        The state also contains current time, current distance and
        the next pod which is supposed to go to a station in the next state.
        """

        def __init__(self):
            self.place_to_pod = {}
            self.output_stations = {}
            self.t = 0
            self.total_costs = 0
            # I should add next task here later.

    def __init__(self):
        self.stations = {}
        self.num_pods = 0
        self.num_places = 0
        self._num_stations = 0

        # Create mapping place to pod
        self.place_to_pod = MMapping()
        # Save mapping pod->station. It is an injective mapping.
        self.pod_to_station = {}
        # The information about station->pods is stored in
        # The each station separately.PlaceDoesNotExist
        # Therefore we do not need self.output_station_to_pod

        # Set initial time
        self.t = 0
        # Set total costs so far
        self.total_costs = 0.0
        self.departure_generator = None  # a function which ask for a pod to be assigned to a station.
        self.solver = None
        self.costs = None
        self._cached_available_places = None

    def set_num_pods(self, n: int):
        """Set number of pods in the system.

        Call this function before, assign pods to places.
        """
        self.num_pods = n

    def set_num_places(self, n: int):
        """Set number of places in the system.

        Call this function before assigning pods to places.
        """
        # Add missing places to place_to_pod function
        # if N is larger than current number of places.
        for place_id in range(self.num_places + 1, n + 1):
            self.place_to_pod[place_id] = INVALID_ID

        # Remove too large point_id if N is smaller than the previous N
        for place_id in range(n + 1, self.num_places + 1):
            del self.place_to_pod[place_id]

        self.num_places = n

    @property
    def places(self):
        """Return all places of the system."""
        return range(1, self.num_places + 1)

    def _update_available_places(self):
        self._cached_available_places = []
        for (place_id, pod_id) in self.place_to_pod.items():
            if pod_id is INVALID_ID:
                self._cached_available_places.append(place_id)

        # Consider next place when this function called outside of solver.decide_new_place.
        if len(self.departure_generator)> 0:
            self._cached_available_places.append(self.place_by_pod(self.departure_generator.current()[0]))
        # Return places always in the same order. This should make the system dynamics more reproducible.
        self._cached_available_places = sorted(self._cached_available_places)

    @property
    def available_places(self):
        if self._cached_available_places is None:
            self._update_available_places()
        return self._cached_available_places

    @property
    def pods(self):
        """Return all the pods of the system."""
        return range(1, self.num_pods + 1)


    # Change later to the station.
    def add_station(self, station: Station):
        """
        :param station: add station to the system.
        """
        self.stations[station.id] = deepcopy(station)

    def station_of_the_pod(self, pod_id):
        for station in self.stations.values():
            if pod_id in station.state:
                return station.id

        return None  # Nothing found.

    def assign_pod_to_place(self, pod_id: int, place_id: int):
        """Add pod into the system. It must be assigned to an existing empty place.

        :param pod_id: ID of a pod to be assign to a place. The ID must be between 1 and number of pods in the system.
        :param place_id: ID of the place where put the pod. The ID must be between 1 und number of places.

        .. note::

           An exception will be raised if you try to assign a pod to a place already assigned to the same pod before.
        """
        if pod_id < 1 or pod_id > self.num_pods:
            raise PodDoesNotExist("Cannot put pod {} to a place {}.".format(pod_id, place_id), pod_id)

        if place_id < 1 or place_id > self.num_places:
            raise PlaceDoesNotExist("Cannot assign pod {} to a place.".format(pod_id), place_id)

        # Assign the pod only to an empty place.
        if not self.place_is_free(place_id):
            raise PlaceNotEmpty("Cannot assign plot. The place is busy with {}".format(
                self.place_to_pod[place_id]), place_id)

        # Add pod to the system if it was not already added to some place
        # or some station.
        assigned_by = self.place_to_pod.get_inverse(pod_id)
        if len(assigned_by) > 1:
            raise PodLocationNotUnique("The pod is already assigned to the place {}".format(assigned_by[0]))

        if self.station_of_the_pod(pod_id) is not None:
            raise PodLocationNotUnique(
                "The pod is already assigned to the station {}".format(self.station_of_the_pod(pod_id)), pod_id)

        self.place_to_pod[place_id] = pod_id

    def assign_pod_to_station(self, pod_id: int, station_id: int):
        """
        Equeue an existing pod into a station id.

        :param pod_id: ID of the Pod. The ID must be between 1 and maximal number of pods.
        :param station_id: id of the station where put the pod. The corresponding
            station must be previously added by :meth:`add_output_station`.
        """
        if 1 < pod_id > self.num_pods:
            raise PodDoesNotExist("Cannot assign pod %d to a station %d." % (pod_id, station_id), pod_id)

        station = self.stations[station_id]
        if station is None:
            raise StationDoesNotExist("Cannot assign pod.", station_id)

        # Add pod to the station.
        station.enqueue(pod_id=pod_id)
        # Update system mappings.
        self.pod_to_station[pod_id] = station_id

    def place_by_pod(self, pod_id):
        """Return place id of a pod.

        :return: ID of the place with the pod, if the pod is in the storage.
        :return None: if the pod is not in the storage.
        """
        inv_image = self.place_to_pod.get_inverse(pod_id)
        if len(inv_image) == 0:
            return None
        elif len(inv_image) == 1:
            return next(iter(inv_image))
        else:
            raise Inconsistency(
                "The a time t={}, the inverse mapping of pod_id {} must be 0 or 1 but it is {} intead.".format(
                    self.t, pod_id, inv_image))

    def pod_by_place(self, place_id):
        """Return ID of the pod in the place."""
        return self.place_to_pod[place_id]

    def set_departure_generator(self, generator: DepartureGenerator):
        """Set a function which will request a pod to move to a particular station in the next system step.

        See :class:`TaskGenerator`.
        """
        self.departure_generator = generator


    def set_costs(self, costs: Costs):
        """Set costs function."""
        self.costs = costs

    def move_pod_from_station(self, pod_id: int, station_id: int, place_id: int):
        """Move pod from station to a place.

        The pod must be valid. Update total distance of the warehouse.

        :return: ID of the moved pod.
        """
        station = self.stations[station_id]
        if pod_id == INVALID_ID:
            raise NotFound("No valid pod to leave the station %d." % station_id)
        # Check if the place is free
        if self.place_to_pod[place_id] != INVALID_ID:
            raise PlaceNotEmpty("Cannot assign pod. The place is busy with {}. t={}".format(
                self.place_to_pod[place_id], self.t), place_id)

        station.former_head = INVALID_ID
        # Add costs for the movement.
        self.total_costs += self.costs.from_station(station_id=station_id, place_id=place_id)

        # Update pod<->place mapping.
        self.place_to_pod[place_id] = pod_id
        # Update pod<->station mapping.
        self.pod_to_station[pod_id] = INVALID_ID
        return pod_id

    def move_pod_to_station(self, pod_id: int, station_id: int):
        """Move pod from its place and put it into a output station.

        The distances of the pod will be updated.
        The total distance will be updated.

        :param pod_id: id of the pod to be moved. The pod must be on some place
        :param station_id: id of the station station where the pod must be moved.

        :return former head of the station if the station was full before.
        :return  :attr:`INVALID_ID` when the station was not full.

        see :meth:`objects.Station.enqueue`
        """
        # Determine the place
        place_id = self.place_by_pod(pod_id)
        if place_id is None:
            raise PodNotInStorage("Departure is not possible", pod_id)

        # Remove place from the pod<->place mappings
        self.place_to_pod[place_id] = INVALID_ID
        # Update distance information. Add the distance to the station.
        self.total_costs += self.costs.to_station(place_id, station_id)
        return self.stations[station_id].enqueue(pod_id)

    def _on_next_task_selected(self, t, pod_id, station_id):
        """This is a callback function is not a part of the mathematical model.

        It can be used by derived class for example to store generated data.
        """
        pass

    def _on_action_selected(self, t, pod_id, station_id, place_id):
        """This is a callback function is not a part of the mathematical model.

        It can be used by derived class for example to store generated data.
        """
        pass

    def _next_station_to_deque(self):
        """If there are no new tasks, we need to decide, which queue needs to be emptied.

        Just empty queues in the orders of their ID is.
        """
        station_ids = self.stations.keys()
        for station_id in sorted(station_ids):
            station = self.stations[station_id]
            if station.former_head != INVALID_ID:
                raise Inconsistency("There must not be former head at the station %d" % station_id)
            if len(station) > 0:
                return station_id
        return INVALID_ID

    def next_arrival_to_storage(self):
        """Return next pod which must be repositioned.

        :return (pod_id, from): return pod for repositioning and the station it leaves.
        :return (INVALID_ID, INVALID_ID): if no pod must be repositioned in the next step.
        """
        # Stop when there is no more departure.
        if len(self.departure_generator) == 0:
            return (INVALID_ID, INVALID_ID)

        # First move pod to a station.

        (pod_id, station_id) = self.departure_generator.current()

        if pod_id != INVALID_ID:
            if self.stations[station_id].is_full():
                return (self.stations[station_id].state[0], station_id)

        return (INVALID_ID, INVALID_ID)

    def next(self, place: int):
        """Move current pod to a new place and go to the next state.

        :return place: place where to put the current pod
        :return True: if the warehouse problem is not finished.
        :return False: if the warehouse problems stops.
        """
        # if tasks are empty stop
        if len(self.departure_generator) == 0:
            return False

        # First move pod to a station.
        (pod, station_id) = self.departure_generator.current()
        self._on_next_task_selected(self.t, pod, station_id)

        (pod_to_reposition, from_station_id) = self.next_arrival_to_storage()
        if pod != INVALID_ID:
            # Enqueue the pod to the station and update costs.
            self.move_pod_to_station(pod, station_id)

        # If one pod needs to leave the station, move it to the new place.
        if pod_to_reposition != INVALID_ID:
            # Move leaving pod from station to new place and update costs.
            self.move_pod_from_station(pod_to_reposition, from_station_id, place)

        # Update time.
        self.t += 1
        # Move to the next departure if there is one.
        self.departure_generator.next()
        if len(self.departure_generator) > 0:
            self._update_available_places()
            logging.debug("Next departure at t = {} is {}".format(self.t, self.departure_generator.current()))
            return True
        else:
            return False

    def finished(self):
        """Is problem finished?"""
        return len(self.departure_generator) == 0

    def get_mathematical_state(self) -> MathematicalState:
        ret_val = Warehouse.MathematicalState()
        for place_id, pod_id in self.place_to_pod.items():
            if pod_id is not None:
                ret_val.place_to_pod[place_id] = pod_id
            else:
                ret_val.place_to_pod[place_id] = INVALID_ID

        for station in self.stations.values():
            ret_val.output_stations[station.id] = deepcopy(station.get_math_state())

        ret_val.t = self.t
        ret_val.total_costs = self.total_costs
        # This part is not complete, because we need all future tasks here.
        if self.departure_generator is None:
            ret_val.next_pod_movement = None
        else:
            ret_val.next_pod_movement = deepcopy(self.departure_generator.current())

        return ret_val

    def empty_storage_area(self):
        """Remove all pods from the storage."""
        for place_id, pod_id in self.place_to_pod.items():
            self.place_to_pod[place_id] = INVALID_ID

    def empty_stations(self):
        """Remove pods from stations."""
        for station in self.stations.values():
            station.delete_pods()

    def delete_pods(self):
        """Remove all pods from the warehouse."""
        # Empty storage area.
        self.empty_storage_area()
        # Empty stations.
        for station in self.stations.values():
            station.delete_pods()
        self.pod_to_station = {}

    def place_is_free(self, place_id):
        """Check if the place is free.

        :return True: if a place with ID **place_id** is free.
        :return False: otherwise
        """
        return self.place_to_pod[place_id] == INVALID_ID
