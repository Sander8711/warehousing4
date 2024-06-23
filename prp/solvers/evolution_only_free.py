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

"""Assign pods using evolutionary algorithms. The genome consists of indices of the free place according
to some fix order. If the index is larger than there are free places we take modulo number of free places.

.. moduleauthor: Ruslan Krenzler

18. Juli 2018.
"""
import copy
import prp.core.objects
from prp.core.objects import INVALID_ID
import prp.stats
import prp.core.costs
import prp.xy
from prp.stats import copy_warehouse
from prp.solvers.simple import PlaybackSolver, RandomSolver, CheapestPlaceSolver, CostsType

class _OrderedSolver:
    """Evaluate system"""
    def __init__(self, warehouse, free_positions):
        self.warehouse = warehouse
        self.free_positions = free_positions
        self.next_entry = 0
        self.translation = []
        self.place_order = None
        self._order_map = None

    def decide_new_place(self):
        (pod, station_id) = self.warehouse.next_arrival_to_storage()
        # No pod must leave any station, skip it.
        if pod == INVALID_ID:
            return INVALID_ID

        if self.next_entry < len(self.free_positions):
            free_pos = self.free_positions[self.next_entry]
            # Make the free position within the range of free places.
            self.next_entry += 1
            # Convert position to a place id.
            # Correct possible effecst of the random mutation, which can make the free position index to become
            # too large.
            av_places = self.available_places()
            free_pos = free_pos % len(av_places)
            return av_places[free_pos]

        return INVALID_ID  # Default solution means no new place. #Add an exception later.

    def available_places(self):
        """Get available places sorted by the place order."""
        return sorted(self.warehouse.available_places, key=lambda x: self._order_map[x])

    def set_place_order(self, place_list):
        self.place_order = copy.deepcopy(place_list)
        # Create place->index map according to its order. This will speed up sorting of available places
        self._order_map = dict(zip(self.place_order, list(range(0, len(place_list)))))

class SolverTranslator(PlaybackSolver):
    """Translate problem solution (places) into a genome (place index)."""

    def __init__(self, warehouse, solver):
        super(SolverTranslator, self).__init__([])
        self.warehouse = warehouse
        self.solver = solver
        self.translation = []
        self.place_order = None

    def decide_new_place(self):
        place_id = self.solver.decide_new_place()
        if place_id != INVALID_ID:
            free_pos = self.get_free_position(place_id)
            self.translation.append(free_pos)
        # Check if the place is
        return place_id

    def get_free_position(self, place_id):
        # Convert position to a place id
        curr_free_pos = 0
        for curr_place_id in self.place_order:
            if curr_place_id not in self.warehouse.available_places:
                continue
            if curr_place_id == place_id:
                return curr_free_pos
            curr_free_pos += 1
        # function must not reach here
        raise prp.warehouse.PlaceNotEmpty("Place is not empty", place_id)

    def set_place_order(self, place_list):
        self.place_order = copy.deepcopy(place_list)


class Helper:
    def __init__(self, system, place_order):
        """Initialize helper class with a system and and place order.

        :param system: which will be used for evaluation.
        :param place_order: list of places according to which available places will be sorted.
            Usually the closes places are in the front."""

        self.orgn_system = system
        self.place_order = place_order
        self.infeasible_costs = self._calculate_infeasible_costs()

    def evaluate(self, individual)->float:
        """Return average costs of the system solved with information in individual.

        :param individual: sequence of indices of free places.
        """
        warehouse = copy_warehouse(self.orgn_system, deep_copy_costs=False)
        ordered_solver = _OrderedSolver(warehouse, individual)
        ordered_solver.set_place_order(self.place_order)

        require_decision = True
        while require_decision:
            place_id = ordered_solver.decide_new_place()
            require_decision = warehouse.next(place_id)

        return (warehouse.total_costs / warehouse.t,)

    def ordered_to_original(self, individual):
        """Convert indivdual to solution (sequence of places)."""
        # Reset system.

        warehouse = copy_warehouse(self.orgn_system, deep_copy_costs=False)
        ordered_solver = _OrderedSolver(warehouse, individual)
        ordered_solver.set_place_order(self.place_order)

        solution = []
        require_decision = True
        while require_decision:
            place_id = ordered_solver.decide_new_place()
            solution.append(place_id)
            require_decision = warehouse.next(place_id)

        return solution

    def _create_individual(self, system_copy, solver):
        """Copy of the system whom solver will solve."""
        translator = SolverTranslator(system_copy, solver)
        translator.set_place_order(self.place_order)

        while not system_copy.finished():
            place_id = translator.decide_new_place()
            system_copy.next(place_id)

        return translator.translation

    def cheapest_place_solution(self, costs_type = CostsType.FROM_STATION_ONLY):
        """Create an individual which corresponds to the cheapest-place solution."""
        system_copy = copy.deepcopy(self.orgn_system)
        solver = CheapestPlaceSolver(system_copy, costs_type=costs_type)
        return self._create_individual(system_copy, solver)

    def random_solution(self):
        """Create a random feasible indidual."""
        system_copy = copy.deepcopy(self.orgn_system)
        solver = RandomSolver(system_copy)
        return self._create_individual(system_copy, solver)

    @staticmethod
    def min_action():
        return 1

    @staticmethod
    def max_action():
        # return max(self.system.places.keys()). We use very large volume to create very uniformly distributed
        # mutations. The actual action is then modulo number of free places.
        return 100000000

    def _calculate_infeasible_costs(self):
        max_to_station = 0.0
        max_from_station = 0.0
        for station_id in self.orgn_system.stations.keys():
            for place_id in self.orgn_system.places:
                max_to_station = max(max_to_station, self.orgn_system.costs.to_station(place_id, station_id))
                max_from_station = max(max_from_station, self.orgn_system.costs.from_station(station_id, place_id))

        return 10 * (max_to_station + max_from_station)
