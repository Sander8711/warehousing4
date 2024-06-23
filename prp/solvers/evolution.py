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

"""Assign pods using evolutionary algorithms.

.. moduleauthor: Ruslan Krenzler

18. Juli 2018.
"""
import prp.solvers.simple as simple
from prp.stats import copy_warehouse


class Helper:
    def __init__(self, system):
        self.orgn_system = copy_warehouse(system)
        # Store costs separatelly. We do not whant copy it
        self.orgn_costs = system.costs
        system.costs = None
        self.infeasible_costs = self.calculate_infeasible_costs()
        # Do not use multiprocessing if you want to have proper evaluation statistis.
        self.evaluation_counter = 0
        self.infeasible_solution_counter =  0

    @staticmethod
    def _create_individual(warehouse, solver):
        """ Return solution of the warehouse with the solver.

        :param warehouse: Copy of the system whom solver will solve.

        .. note: this function changes warehouse.
        """
        # Run the system until no departure left. Store solution.
        solution = []

        require_decision = True
        while require_decision:
            place_id = solver.decide_new_place()
            solution.append(place_id)
            require_decision = warehouse.next(place_id)

        return solution

    def cheapest_place_solution(self):
        system_copy = copy_warehouse(self.orgn_system)
        solver = simple.CheapestPlaceSolver(system_copy)
        return self._create_individual(system_copy, solver)

    def random_solution(self):
        system_copy = copy_warehouse(self.orgn_system)
        solver = simple.RandomSolver(system_copy)
        return self._create_individual(system_copy, solver)

    def reset_counters(self):
        self.evaluation_counter = 0
        self.infeasible_solution_counter =  0

    def evaluate(self, individual):
        # Reset system
        warehouse = copy_warehouse(self.orgn_system, deep_copy_costs=False)
        self.evaluation_counter += 1
        try:
            i = 0
            while not warehouse.finished():
                warehouse.next(individual[i])
                i += 1
            return (warehouse.total_costs/warehouse.t,)
        except Exception as e:
            self.infeasible_solution_counter += 1
            return (self.infeasible_costs,)

    def min_action(self):
        return 1

    def max_action(self):
        return self.orgn_system.num_places

    def calculate_infeasible_costs(self):
        max_to_station = 0.0
        max_from_station = 0.0
        for station_id in self.orgn_system.stations.keys():
            for place_id in self.orgn_system.places:
                max_to_station = max(max_to_station, self.orgn_costs.to_station(place_id, station_id))
                max_from_station = max(max_from_station, self.orgn_costs.from_station(station_id, place_id))

        return 10 * (max_to_station + max_from_station)
