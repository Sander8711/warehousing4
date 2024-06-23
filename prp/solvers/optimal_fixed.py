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

"""This module finds an initial state of warehouse optimal for fixed-place policy.

.. moduleauthor: Ruslan Krenzler

4. September 2018.
"""


import logging
import pulp
import prp.core.objects
from prp.core.objects import INVALID_ID
import prp.stats
import prp.core.costs
import prp.xy


class _DetermineOptimal:
    def __init__(self, orgn_warehouse):
        self.t_init = orgn_warehouse.t  # Save initial time.
        self.N = len(orgn_warehouse.departure_generator)  # Save last departure time + 1
        # Save occupations sorted by arrival times.
        occupations = self.get_occupations(orgn_warehouse)
        # Calculate times when a place must be assigned. The pod is not allowed
        # to stay in the queue in the next time step.
#        self.must_take_actions_T = self.calculate_action_times(self.occupations)
        self.Pl = orgn_warehouse.places
        self.Pd = orgn_warehouse.pods
        self.St = orgn_warehouse.stations.keys()

        self.costs = prp.core.costs.DictCosts(orgn_warehouse.costs)
        self.from_counts = self.calculate_from_station_count(occupations)
        self.to_counts = self.calculate_to_station_count(occupations)

    @staticmethod
    def get_occupations(warehouse):
        """Get occupation times sorted by arrival times."""
        occupations = prp.stats.get_occupations(warehouse)
        # Sort occupations by arrival times
        occupations = sorted(occupations, key=lambda oc: oc.begin)
        return occupations

    def _empty_counts(self):
        res = {}
        for place_id in self.Pl:
            # Init stations frequencies with 0 first.
            res[place_id] = {}
            for station_id in self.St:
                res[place_id][station_id] = 0
        return res

    def calculate_from_station_count(self, occupations):
        res = self._empty_counts()
        # Fill station occurencies.
        for occupation in occupations:
            st_id = occupation.from_station_id
            if st_id is not INVALID_ID:
                res[occupation.pod_id][st_id] += 1
        return res

    def calculate_to_station_count(self, occupations):
        res = self._empty_counts()
        # Fill station occurrences.
        for occupation in occupations:
            st_id = occupation.to_station_id
            if st_id is not INVALID_ID:
                res[occupation.pod_id][st_id] += 1
        return res

    def calculate_optimal_assigment(self):
        problem = pulp.LpProblem("Warehouse", pulp.LpMinimize)
        logging.info("Creating decision variables...")
        x = self.get_decision_variables()
        logging.info("Adding cost functions...")
        cs = self.get_costs()
        problem += pulp.lpSum([cs[name] * x[name] for name in x.keys()])

        logging.info("Adding \"maximal one pod per place.\" constraints")
        for place_id in self.Pl:
            index_subset = []
            for pod_id in self.Pd:
                name = "x_%d_%d" % (pod_id, place_id)
                index_subset.append(name)
            problem += pulp.lpSum(x[name] for name in index_subset) <= 1

        # Or is the sum better?
        logging.info("Adding \"Assign every pods\" constraints")
        for pod_id in self.Pd:
            index_subset = []
            for place_id in self.Pl:
                name = "x_%d_%d" % (pod_id, place_id)
                index_subset.append(name)
            problem += pulp.lpSum(x[name] for name in index_subset) == 1

        logging.info("Total constraints number: %d." % len(problem.constraints))
        # print(problem)
        logging.info("Solving problem...")
        problem.solve()
        logging.info("Complete.")
        logging.info("Status: {}".format(pulp.LpStatus[problem.status]))
        # Convert BP solution back to actions
        a_fix = self._convert_solution_to_action_function(problem.variables())
        return (a_fix, problem)

    def _convert_solution_to_action_function(self, solution):
        """Convert mixed integer solution to pod->place map."""
        a_fix = {}
        for v in solution:
            if v.varValue == 1:
                sub_str = v.name.split("_")
                (pod_id, place_id) = (int(sub_str[2]), int(sub_str[3]))
                a_fix[pod_id] = place_id

        return a_fix

    def get_decision_variables(self):
        # Create a dictionary with variable names.
        # map names to (t,p) indices.
        x_names = []
        for pod_id in self.Pd:
            for place_id in self.Pl:
                name = "x_%d_%d" % (pod_id, place_id)
                x_names.append(name)
        x = pulp.LpVariable.dict("Decision", x_names, lowBound=0, upBound=1, cat=pulp.LpInteger)
        logging.info("Number of decision variables: %d." % len(x_names))
        return x

    def total_costs(self, pod_id, place_id):
        costs = 0
        for station_id in self.St:
            costs += self.from_counts[pod_id][station_id] * self.costs.from_station(station_id, place_id)\
                + self.to_counts[pod_id][station_id] * self.costs.to_station(place_id, station_id)
        return costs

    def get_costs(self):
        cs = {}
        for pod_id in self.Pd:
            for place_id in self.Pl:
                name = "x_%d_%d" % (pod_id, place_id)
                cs[name] = self.total_costs(pod_id, place_id)
        return cs


def optimal_assignment(warehouse):
    """Find optimal fixed places."""
    init = _DetermineOptimal(warehouse)
    (a_fix, problem) = init.calculate_optimal_assigment()
    return a_fix


def _get_average_place_costs(station_frequnces, costs):
    # Calculate station weights.
    w = {}
    n = sum(station_frequnces.values())
    for (fid, f) in station_frequnces.items():
        w[fid] = f / n

    avg_costs = prp.core.costs.AverageCosts(costs, w)
    return avg_costs.average_mapping


def _get_sorted_places(station_frequencies, costs):
    """Sort places by their average costs."""
    avg_costs = _get_average_place_costs(station_frequencies, costs)
    places = list(avg_costs.keys())
    return sorted(places, key=lambda x: avg_costs[x])


def _get_sorted_pods(pod_frequences):
    pods = list(pod_frequences.keys())
    return sorted(pods, key=lambda x: pod_frequences[x], reverse=True)


def init_appx_optimally(warehouse):
    """Get statistics of the departures."""
    dep_stats = prp.stats.get_marginal_frequencies(warehouse.departure_generator)
    sorted_places = _get_sorted_places(dep_stats.station_usage, warehouse.costs)
    sorted_pods = _get_sorted_pods(dep_stats.pod_usage)
    a_fix = {}
    for i in range(0, len(sorted_pods)):
        a_fix[sorted_pods[i]] = sorted_places[i]

    return a_fix


def get_place_costs(warehouse):
    """Calculate average costs of places in the warehouse dependent on station usage."""
    dep_stats = prp.stats.get_marginal_frequencies(warehouse.departure_generator)
    return _get_average_place_costs(dep_stats.station_usage, warehouse.costs)


def reassign(warehouse, pos):
    """Reassign pods according to fixed position pos.

    :param pos: Dictionary pod->place.
    """
    warehouse.empty_storage_area()
    warehouse.empty_stations()
    for (pod_id, place_id) in pos.items():
        warehouse.assign_pod_to_place(pod_id, place_id)
