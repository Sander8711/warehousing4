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
"""Mathematical objects for a warehouse simulation.

21 November 2017

.. moduleauthor:: Ruslan Krenzler
"""

#: Invalid pod, place or station ID.
INVALID_ID = 0


class Station:
    """Output station. It is a queue with finite number of places.

    Set parameter of the system on initialization. Be careful. Do not change it mathematical state
    directly. It refers to the internal members of the system and may change system consistency.
    If you want to edit the mathematical state make a deepcopy of it.

    .. data:: id

        Id of the output station.

    .. data:: max_n

        Parameter of the system. it is maximal number of pods in the queue.

    .. data:: state

        This is a mathematical representation of a station state.
        Its type is a python list.
        *State* means "a part of the system which frequently changes".
        It is a sequence of the pods in the queue beginning
        with the pod at the queue head.
        Example:    :math:`\\left\\langle 3,4,1\\right|`

    .. note::

       The following suggestions can help to keep the station-object consistent:

       * To change the state of the object use :meth:`enqueue`, :meth:`dequeue` and :meth:`delete_pods`.
       * Do not change states returned by :meth:`get_math_param` and :meth:`get_math_state`
         because they can refer to internal data.
    """

    def __init__(self, id, n):
        """Set parameters of the output station.

        :param id: Id of the station.
        :param n: Maximal number of pods in the station including the queue.
        """
        self.id = id
        self.max_n = n
        self.state = []

    def enqueue(self, pod_id: int) -> int:
        """Add a pod into queue.

        When the queue is too long, the 0th element
        will be pushed out and returned.

        :param pod_id: ID of the pod.

        :return valid pod id: if the new pod_id pushed the pod_id in the head out. This is when the queue
            was full before new pod arrived.

        :return :attr:`INVALID_ID`: if there was enough space for the new pod.
        """
        # If the queue already has its maximus size, remove the pod from the queue head
        # and store it into former_head.
        former_head = INVALID_ID
        if len(self.state) >= self.max_n:
            former_head = self.state.pop(0)

        # push pod id to the queue
        self.state.append(pod_id)
        # Return the old pod at the head.
        return former_head

    def dequeue(self) -> int:
        """Remove pod from the queue.

        :returns: the former head pod or :attr:`INVALID_ID` if the queue was empty before.
        """
        former_head = INVALID_ID
        if (len(self.state) > 0):
            former_head = self.state.pop(0)

        return former_head

    def get_math_param(self) -> int:
        """Return mathematical representation of the output station parameters.

        see :class:`OutputStation`.
        :returns: maximal number of pods.
        """
        return self.max_n

    def get_math_state(self) -> list:
        """Return mathematical representation of the object."""
        return self.state

    def set_math_state(self, state: list):
        """Set state of the station."""
        self.state = state

    def delete_pods(self):
        """Empty queue."""
        self.state = []

    def __len__(self):
        """Return number number of pods in the station."""
        return len(self.state)

    def is_full(self):
        """Return true if the station is full"""
        return len(self.state) == self.max_n

class Costs:
    """Calculate different costs of a system."""
    @property
    def station_ids(self):
        pass

    @property
    def place_ids(self):
        pass

    def from_station(self, station_id: int, place_id: int):
        pass

    def to_station(self, place_id, station_id):
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
        """Setup constant costs.

        :param station_ids: station domain of the function.
        :param place_ids: place domain of the function.
        :param from_station: Constant costs from every station.
        :param to_station: Constant costs to every station (default equal to from-costs).
        """
        self._from_station = from_station
        if to_station is None:
            self._to_station = from_station
        else:
            self._to_station = to_station

    def from_station(self, station_id: int, place_id: int):
        return self._from_station

    def to_station(self, place_id, station_id):
        return self._to_station
