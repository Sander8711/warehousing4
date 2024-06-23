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
"""This is a tetris solver for the pod assignment problem.

It uses most-expensive-place solver as for an initial solution.

.. moduleauthor: Ruslan Krenzler

26. June 2018.
"""

import logging
from enum import Enum
from collections import namedtuple
from sortedcontainers import SortedKeyList
import numpy
import prp.stats
import prp.core.costs
from prp.core.objects import INVALID_ID
from prp.solvers.simple import CheapestPlaceSolver, CostsType


class OccupationPriority(Enum):
    POD_FREQUENCY = 1
    SOJOURN_TIME = 2
    DEPARTURE = 3

_ArrivalEntry = namedtuple('ArrivalEntry', ['t', 'pod', 'place'])


class _OccupiedTime:
    """Store occupied time as a sequence of busy intervals."""

    def __init__(self):
        # Intervals are triplets (pod_id, begin, end). They describe a time from begin,
        # including the begin, until end, excluding the end, sorted by begin.
        self.intervals = SortedKeyList([], key=lambda val: val.begin)
        self.max_end = None

    @classmethod
    def intersects(cls, a1, b1, a2, b2):
        if a1 <= a2 < b1:
            return True
        if a1 < b2 <= b1:
            return True
        if a2 < a1 and b2 > b1:
            return True
        return False

    def is_free(self, begin, end):
        for interval in self.intervals:
            if self.intersects(interval.begin, interval.end, begin, end):
                return False
        return True

    def occupy(self, interval):
        if self.max_end is not None:
            self.max_end = max(self.max_end, interval.end)
        else:
            self.max_end = interval.end
        self.intervals.add(interval)

    def initial_interval(self):
        """Return the interval at the beginning.

        :returns interval: if there is an interval in the beginning.
            None: if there is no interval in the beginning.
        """
        if len(self.intervals) > 0:
            return self.intervals[0]
        else:
            return None

    def del_interval(self, begin):
        # Delete interval which begins with *begin*.
        it = self.intervals.irange_key(begin, begin)
        old_interval = next(it)
        self.intervals.remove(old_interval)
        return old_interval


def _get_init_occupation_table(occupations, all_places, t_start=0):
    """Create an occupation table with initial constraints.

    Return occupation table indexed by places.

    Note, the *occupations* list may not have information about all available places in the system,
    that is why this list must be provided separately.

    @:param t_start: starting time of the simulation. It is used to determine which occupations are part
                    of initial constraints.

    :param all_places: ids of all places in the system.
    """
    table = {}
    for place_id in all_places:
        if place_id not in table.keys():
            table[place_id] = _OccupiedTime()

    for occ in occupations:
        if occ.begin < t_start:
            table[occ.place_id].occupy(occ)
    return table


def _get_occupation_table_by_place(occupations, all_places):
    """Create an occupation table.

    Return occupation table indexed by places.

    Note, occupations list may not have information about all available places in the system,
    that is why this list must be provided separately.

    :param all_places: ids of all places in the system.
    """
    table = {}
    for place_id in all_places:
        if place_id not in table.keys():
            table[place_id] = _OccupiedTime()

    for occ in occupations:
        table[occ.place_id].occupy(occ)
    return table


def _get_occupations_by_pod(occupations, all_places, t_begin=0):
    """Return occupation times grouped by pods.

    Ignore occupation which arrives before *t_start*, because these occupations are part of the initial conditions.
    They cannot be changed.
    """
    table = {}

    for place_id in all_places:
        if place_id not in table.keys():
            table[place_id] = _OccupiedTime()

    for occ in occupations:
        if occ.begin >= t_begin:
            interval = prp.stats.Occupation(place_id=occ.place_id, begin=occ.begin, end=occ.end,
                                            from_station_id=occ.from_station_id, to_station_id=occ.to_station_id)
            table[occ.pod_id].occupy(interval)
    return table


def _calc_pod_priporities_by_frequency(occupations):
    """Calculate global pod priorities based on the pod usage.

    More frequent pods have higher priority. They are in the beginning.
    """
    x = []
    for occ in occupations:
        x.append(occ.pod_id)
    x = numpy.array(x)
    key, freq = numpy.unique(x, return_counts=True)
    x = zip(key, freq)
    # Sort by frequency
    x = sorted(x, key=lambda val: val[1], reverse=True)
    logging.debug("Pod frequencies:")
    logging.debug(x)
    x0, x1 = zip(*x)
    return x0


def _arrivals_to_solution(arrivals, t_begin=0):
    """Recovery solution from arrival data."""
    x = sorted(arrivals, key=lambda val: val.t)
    # remove time and pod
    solution = []
    for entry in x:
        # We assume that the solution begins with time t_begin, if
        # x does not contain data for all times, we insert 0
        # (no action) as a missing solution
        # Note that the arrival is 1 time unite later after the action
        # is decided therefore we compare (entry.t-1) and not (entry.t)
        while len(solution) < (entry.t + t_begin - 1):
            solution.append(0)
        solution.append(entry.place)
    return solution


def _assign_by_frequency(pod_priorities, place_priorities, occupation_table, occupations, t_begin=0):
    occupations_by_pod = _get_occupations_by_pod(occupations, t_begin)

    # Sort higher priority pods first
    for curr_pod in pod_priorities:
        pods_occupation = occupations_by_pod[curr_pod]  # Occupations information from the point of view of the
        # current pod. That means it time, future station, and place.
        # Place can be inorred it is only used for debugging.
        for pods_interval in pods_occupation.intervals:
            begin = pods_interval.begin
            end = pods_interval.end
            from_station_id = pods_interval.from_station_id
            to_station_id = pods_interval.to_station_id
            # Check if we have enough places
            found = False  # for debugging.
            for place in place_priorities:
                if occupation_table[place].is_free(begin, end):
                    interval = prp.stats.Occupation(pod_id=curr_pod, begin=begin, end=end,
                                                    from_station_id=from_station_id, to_station_id=to_station_id)
                    occupation_table[place].occupy(interval)
                    found = True
                    break
            if not found:
                logging.error("ERROR: No free place found.")
                break

    return occupation_table


def occupation_table_to_solution(occupation_table, t_begin, t_end):
    arrivals = []
    for (place_id, occupations) in occupation_table.items():
        for interval in occupations.intervals:
            # Ignore interval wich is smaller than t_begin. That means it is a part of inital conditions.
            if interval.begin < t_begin:
                continue
            arrivals.append(_ArrivalEntry(t=interval.begin, pod=interval.pod_id, place=place_id))

    solution = _arrivals_to_solution(arrivals, t_begin)
    # If solution is shorter than t_end - t_begin, then the last actions were 0's.
    # Add missing zeros to solution.
    missing = t_end - t_begin - len(solution)
    if missing > 0:
        solution.extend(missing*[INVALID_ID])
    return solution


def _extract_occupations(table):
    """Extract occuptions from occupation table.

    The occupations are sorted by place.
    """
    result = []
    for (place_id, occupations) in table.items():
        for interval in occupations.intervals:
            result.append(prp.stats.Occupation(place_id=place_id, pod_id=interval.pod_id,
                                               begin=interval.begin, end=interval.end,
                                               span=interval.end - interval.begin,
                                               from_station_id=interval.from_station_id,
                                               to_station_id=interval.to_station_id))

    return result


class MinusCosts(prp.core.costs.Costs):
    """Make the least expensive costs to most the expensive costs."""

    def __init__(self, orgn_costs):
        self.orgn_costs = orgn_costs

    @property
    def station_ids(self):
        return self.orgn_costs.station_ids

    @property
    def place_ids(self):
        return self.orgn_costs.place_ids

    def from_station(self, station_id: int, place_id: int):
        return -self.orgn_costs.from_station(station_id, place_id)

    def to_station(self, place_id: int, station_id: int):
        return -self.orgn_costs.to_station(place_id, station_id)


def pre_solve(warehouse):
    # Make copy here later
    initial = prp.stats.copy_warehouse(warehouse)
    # Collect statistics and create solution with most expensive costs.
    solver = CheapestPlaceSolver(initial, MinusCosts(warehouse.costs),
                                 CostsType.DECISION)
    occupations = prp.stats.get_occupations(initial, solver, do_not_copy=True)
    # Create initial occupation table.
    occupation_table = _get_occupation_table_by_place(occupations, initial.places)
    # Calculate cost.
    w = prp.stats.get_station_frequencies(occupations, absolute=False)
    costs = prp.core.costs.AverageCosts(initial.costs, w)
    return occupation_table, costs


def rearange_occupation_table(occupation_table, place_ids, cost_func, pod_priority_func):
    occupations = _extract_occupations(occupation_table)
    occupations = pod_priority_func(occupations)
    # Change occupation table pod by pod.
    for interval in occupations:
        # ignore not movable occupations.
        if interval.begin < 0:
            continue
        # Check if we find a better place in occupation_table.
        # Calculate costs.
        best_costs = cost_func(interval.from_station_id, interval.place_id, interval.to_station_id)
        best_place = interval.place_id
        # Check if there are cheaper places in the storage.
        for new_place_id in place_ids:
            # Check costs first, they are faster to calculate than occupations.
            curr_costs = cost_func(interval.from_station_id, new_place_id, interval.to_station_id)
            # We found a cheaper place, but is it also free? (A slower operation).
            if curr_costs < best_costs:
                if occupation_table[new_place_id].is_free(interval.begin, interval.end):
                    best_costs = curr_costs
                    best_place = new_place_id
        # If found, move pod from old place to the better place.
        if best_place != interval.place_id:
            # Remove interval from the old place.
            old_interval = occupation_table[interval.place_id].del_interval(interval.begin)
            # Put interval to the new place.
            occupation_table[best_place].occupy(old_interval)
    return occupation_table


def _frequency_priority(occupations):
    """Sort occupation by pod frequencies priority and time."""
    pod_priorities = _calc_pod_priporities_by_frequency(occupations)
    logging.debug("Pod priorities:\n{}".format(pod_priorities))

    # First create mapping from a sequence pod_priorities to a dictionary
    # pod->priority. Higher number means higher priority.
    priority = {}
    n = len(pod_priorities)
    for i in range(0, n):
        priority[pod_priorities[i]] = n - i

    # Now sort occupations. Occupation with highest priority of the pod and lower time are in the front.
    return sorted(occupations, key=lambda x: (-priority[x.pod_id], x.begin))


def _sojourn_time_priority(occupations):
    return sorted(occupations, key=lambda x: x.span)


def _departure_time_priority(occupations):
    return sorted(occupations, key=lambda x: (x.end, x.begin))


def get_cost_function(warehouse, costs_type=CostsType.DECISION):
    if costs_type.value == CostsType.FROM_STATION_ONLY.value:
        def cost_func(from_station, place, to_station):
            return warehouse.costs.from_station(from_station, place)
    #    elif costs_type == Costs.AVERAGE:
    #        def cost_func(from_station, place, to_station): return costs.average_mapping[place]
    #    elif costs_type == Costs.ESTIMATED:
    #        def cost_func(from_station, place, to_station): return costs.estimated_mapping[from_station][place]
    # elif costs_type is CostsType.DECISION:  # Does not work.
    elif costs_type.value is CostsType.DECISION.value:
        def cost_func(from_station, place, to_station):
            res = warehouse.costs.from_station(from_station, place)
            if to_station is not INVALID_ID:
                res += warehouse.costs.to_station(place, to_station)
            return res
    else:
        return None
    return cost_func


def get_occupation_sort(occupation_priority):
    if occupation_priority == OccupationPriority.POD_FREQUENCY:
        return _frequency_priority
    elif occupation_priority == OccupationPriority.SOJOURN_TIME:
        return _sojourn_time_priority
    elif occupation_priority == OccupationPriority.DEPARTURE:
        return _departure_time_priority
    else:
        return None


def solve(warehouse, costs_type=CostsType.DECISION, occ_priority=OccupationPriority.POD_FREQUENCY):
    t_begin = warehouse.t
    t_end = len(warehouse.departure_generator)
    """Solver warehouse problem with tetris."""
    logging.info("Create initial feasible solution:\n")
    # First run prepare a feasible solution whith less frequent pods far away from the output stations.
    (occupation_table, costs) = pre_solve(warehouse)

    # Improve results.
    logging.info("Improve results:\n")
    cost_func = get_cost_function(warehouse, costs_type)
    pod_priority_func = get_occupation_sort(occ_priority)

    occupation_table = rearange_occupation_table(occupation_table, warehouse.places, cost_func, pod_priority_func)

    return occupation_table_to_solution(occupation_table, t_begin, t_end)
