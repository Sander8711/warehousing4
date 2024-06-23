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

"""Collect statistics of a warehouse system:

* Occupation: time interval a pod spends in the storage area.

.. moduleauthor:: Ruslan Krenzler

21 Juni 2018
"""

from collections import namedtuple
import numpy
import prp.core.warehouse as warehouse_mod
from prp.core.objects import INVALID_ID
import prp.solvers.simple
import copy
from prp.core.costs import ZeroCosts

Occupation = namedtuple('Occupation', ['place_id', 'pod_id', 'begin', 'end',
                                       'span', 'from_station_id', 'to_station_id'], verbose=False)


def copy_warehouse(warehouse: warehouse_mod.Warehouse, deep_copy_costs=True):
    """Create a copy of a warehouse with a deterministic departures.

    :param copy_costs (default True): Usually the costs are static, that means, the costs do not change during the
       system run. You can save some time if do not copy them entirely.
       Set deep_copy_costs to True if you want create a deep copy the costs, set it to False if you don't.
    """
    # Copy everything except for costs.
    if deep_copy_costs:
        new_warehouse = copy.deepcopy(warehouse)
    else:
        shallow_copy = copy.copy(warehouse)
        shallow_copy.costs = None
        new_warehouse = copy.deepcopy(shallow_copy)
        # Use old costs.
        new_warehouse.costs = warehouse.costs

    return new_warehouse


def get_occupations(warehouse: warehouse_mod.Warehouse, solver = None, do_not_copy = False):
    """Get occupation statistics of the warehouse with deterministic finite departures."""
    if not do_not_copy:
        warehouse = copy_warehouse(warehouse)
        # We do not care about the costs.
        warehouse.costs = ZeroCosts()

    if solver is None:
        solver = prp.solvers.simple.SomePlaceSolver(warehouse)

    occupations = []
    current_interval = {}
    # Set initial states.
    for place_id in warehouse.places:
        current_interval[place_id] = [float('-inf'), None, INVALID_ID]

    # Add occupation intervals.
    while not warehouse.finished():
        # Calculate which pod goes from which place to which station.
        (to_station_pod, to_station) = warehouse.departure_generator.current()
        from_place = warehouse.place_by_pod(to_station_pod)
        # Calculate whih pod goes to which place from which station.
        to_place = solver.decide_new_place()
        (_, from_station) = warehouse.next_arrival_to_storage()

        # Add finished occupation interval to intervals.
        if from_place is not INVALID_ID:
            interval = current_interval[from_place]
            interval[1] = warehouse.t + 1  # Note. The pod from this place will leave only in the next time step.
            occupations.append(Occupation(place_id=from_place, pod_id=to_station_pod, begin=interval[0],
                                          end=interval[1], span=interval[1] - interval[0],
                                          from_station_id=interval[2],
                                          to_station_id=to_station))
            current_interval[from_place] = None

        # Create new occupation interval.
        if to_place != INVALID_ID:
            current_interval[to_place] = [warehouse.t + 1, float('Inf'), from_station]
        warehouse.next(to_place)

    # Add occupations intervals of places whose pods did not deparured.
    for (place_id, interval) in current_interval.items():
        if interval is not None:
            pod_id = warehouse.place_to_pod[place_id]
            if interval is not None:
                interval[1] = float('inf')
                occupations.append(Occupation(place_id=place_id, pod_id=pod_id, begin=interval[0],
                                              end=interval[1], span=interval[1] - interval[0],
                                              from_station_id=interval[2],
                                              to_station_id=INVALID_ID))

    return occupations


def get_station_frequencies(occupations, absolute=True):
    """Return, how frequently a destionation station occures in occupation data."""
    x = []
    for occ in occupations:
        if occ.to_station_id != INVALID_ID:
            x.append(occ.to_station_id)

    x = numpy.array(x)

    key, freq = numpy.unique(x, return_counts=True)
    result = dict(zip(key, freq))

    # Normalize frequencies if requesteds
    if not absolute:
        n = len(x)
        for (id, freq) in result.items():
            result[id] /= n

    return result


def get_marginal_frequencies(task_generator: warehouse_mod.DepartureGenerator):
    """Get arrival frequency of pods to a particular station.

    :returns: named tupple with two dictionaries. The pod_usage dictionary contains pods and number of their occurrences
      in the generated stream. The station_usage dictionary contains stations ad number of their occurrences.

    .. Warning:
       function changes the task generator.
    """
    station_usage = {}
    pod_usage = {}
    while len(task_generator) > 0:
        (pod_id, station_id) = task_generator.current()
        task_generator.next()
        if pod_id not in pod_usage.keys():
            pod_usage[pod_id] = 1
        else:
            pod_usage[pod_id] += 1

        if station_id not in station_usage.keys():
            station_usage[station_id] = 1
        else:
            station_usage[station_id] += 1

    DepartureStats = namedtuple('DepartureStats', ['pod_usage', 'station_usage'], verbose=False)
    return DepartureStats(pod_usage=pod_usage, station_usage=station_usage)
