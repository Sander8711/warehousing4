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
"""Add recording and playback facility to the warehouse.

.. moduleauthor:: Ruslan Krenzler

21 December 2017

That means storage and loading functions for:

* initial state,
* departures of pods from storage to stations,
* solutions (sequences of places).
"""

import json

import prp.core.objects as objects
import prp.core.warehouse as warehouse_mod
from prp.core.departure_generators import DeterministicDepartures, DepartureGenerator
import prp.solvers.simple
import prp.core.costs as costs_mod


class LayoutEncoder(json.JSONEncoder):
    """This file is used to encode python objects as dictionaries."""

    def default(self, o):  # noqa: D102
        if isinstance(o, objects.Station):
            return {"MaxN": o.max_n}
        elif isinstance(o, warehouse_mod.Warehouse.MathematicalState):
            return {"T": o.t,
                    "Costs": o.total_costs,
                    "PlaceToPod": o.place_to_pod,
                    "OutputStations": o.output_stations,
                    "NextPodMovement": o.next_pod_movement}


def decode_state(o):
    """Help Json to convert plane dictionary data to corresponding python objects."""
    if all(key in o for key in ["T", "D", "PlaceToPod", "OutputStations", "NextPodMovement"]):
        ret_val = warehouse_mod.Warehouse.MathematicalState
        ret_val.t = o["T"]
        ret_val.total_costs = o["Costs"]
        ret_val.place_to_pod = o["PlaceToPod"]
        ret_val.output_stations = o["OutputStations"]
        ret_val.next_pod_movement = o["NextPodMovement"]
        return ret_val
    return o


def convert_keys_to_int(dic: dict):
    """Store numerical keys as numbers.

    Json converts all the dictionary keys to string, this function converts them back to integers
    This function is recursive, until it hits a dictionary without integer keys.
    """
    ret_val = {}
    for key, value in dic.items():
        try:
            int_k = int(key)
        except ValueError:
            return dic  # return original dictionary
        if isinstance(value, dict):
            ret_val[int_k] = convert_keys_to_int(value)
        else:
            ret_val[int_k] = value
    return ret_val


class DepartureRecorder(DepartureGenerator):
    """This generator is a proxy which records departures of another generator."""

    def __init__(self, departure_generator):  # noqa: D102
        self.recorded_departure = None
        self.next_departure_i = 0
        self.other_generator = departure_generator

    def next(self):  # noqa: D102
        self.other_generator.next()
        if len(self.other_generator) > 0:
            self.recorded_departure.append(self.other_generator.current())

    def current(self):  # noqa: D102
        departure = self.other_generator.current()
        if self.recorded_departure is None:
            self.recorded_departure = [departure]
        return departure

    def __len__(self):  # noqa: D102, D105
        return len(self.other_generator)

    def is_finite(self):  # noqa: D102
        return self.other_generator.is_finite()

    def get_all_departures(self):
        """Return a list of all departures as a list of tuples (pod_id, station_id)."""
        return self.recorded_departure

    def store_to_json(self, outfile):
        """Store recorded departures to a JSON file."""
        json.dump(self.recorded_departure, outfile)


def load_departures_from_json(f):
    """Load departures from JSON file.

    :return determinstc departure generator when succeed and None on failure.
    """
    return DeterministicDepartures(json.load(f))


def _decode_state(o):
    """Help JSON to convert dictionary data to corresponding python objects."""
    if all(key in o for key in ["T", "Costs", "PlaceToPod", "OutputStations", "NextPodMovement"]):
        ret_val = warehouse_mod.Warehouse.MathematicalState()
        ret_val.t = o["T"]
        ret_val.total_costs = o["Costs"]
        # Json will storage integer keys as strings. Repair them (convert them back to integers).
        ret_val.place_to_pod = convert_keys_to_int(o["PlaceToPod"])
        ret_val.output_stations = convert_keys_to_int(o["OutputStations"])
        ret_val.next_pod_movement = o["NextPodMovement"]
        return ret_val
    return o


def _get_num_of_pods(math_state):
    ret_val = 0
    for (place_id, pod_id) in math_state.place_to_pod.items():
        if pod_id > 0:
            ret_val += 1
    for (station_id, math_station_state) in math_state.output_stations.items():
        ret_val += len(math_station_state)
    return ret_val


def load_initial_state_from_json(f, warehouse: warehouse_mod.Warehouse):
    """Set initial state of the warehouse from a JSON file.

    :param f: file stream as it retunres by python open
    :param warehouse: warehouse whose initial state must be set.
    """
    loads_initial_state_from_json_string(f.read(), warehouse)


def loads_initial_state_from_json_string(s, warehouse: warehouse_mod.Warehouse):
    """Set initial state of the warehouse from a JSON file.

    :param s: json data.
    :param warehouse: warehouse whose initial state must be set.
    """
    warehouse.delete_pods()
    math_state = json.loads(s, object_hook=_decode_state)
    # Add pods to warehouse.
    warehouse.set_num_pods(_get_num_of_pods(math_state))
    # assign pods to places or to stations
    for (place_id, pod_id) in math_state.place_to_pod.items():
        # Add only if the place is not empty -- that means pod_id is > 0.
        if pod_id > 0:
            warehouse.assign_pod_to_place(pod_id, place_id)
    for (station_id, math_station_state) in math_state.output_stations.items():
        for pod_id in math_station_state:
            warehouse.assign_pod_to_station(pod_id, station_id)

    warehouse.t = math_state.t
    warehouse.total_costs = math_state.total_costs
    warehouse.next_pod_movement = math_state.next_pod_movement  # possible I can ignore this.


def store_initial_state_to_json(warehouse: warehouse_mod.Warehouse, f):
    """Store the inistial state of a warehouse to a JSON file."""
    math_state = warehouse.get_mathematical_state()
    json.dump(math_state, f, cls=LayoutEncoder)


def store_solution_to_json(solution, f):
    """Store solution as a sequence of places to a JSON file."""
    json.dump(solution, f)


def load_solution_from_json(f) -> list:
    """Load solution from json file.

    :return solution as a list of actions.
    """
    return json.load(f)


class CostsEncoder(json.JSONEncoder):
    """This file is used to encode python objects as dictionaries."""

    def default(self, o):
        """Tell JSON how to store a DictCosts object."""
        if isinstance(o, costs_mod.DictCosts):
            return {"NumStations": o.num_stations, "NumPlaces": o.num_places,
                    "ToStation": o.to_station_dict, "FromStation": o.from_station_dict}


def store_costs_to_json(costs: costs_mod.Costs, f):
    """Store costs to a JSON file."""
    if type(objects) != costs_mod.DictCosts:
        costs = costs_mod.DictCosts(costs)

    json.dump(costs, f, cls=CostsEncoder)


def _decode_costs(o):
    """Convert dictionary read by JSON into DictCosts."""
    if all(key in o for key in ["NumStations", "NumPlaces", "ToStation", "FromStation"]):
        ret_val = costs_mod.DictCosts()
        ret_val.set_num_stations(o["NumStations"])
        ret_val.set_num_places(o["NumPlaces"])
        # Read to-station dictionary.
        str_dict = o["ToStation"]
        # Convert strings to integers keys and float numbers.
        for (place_id, stations) in str_dict.items():
            for (station_id, costs) in stations.items():
                ret_val.set_to_station(int(place_id), int(station_id), float(costs))

        # Read from-station dictionary.
        str_dict = o["FromStation"]
        # Convert strings to integers keys and float numbers.
        for (station_id, places) in str_dict.items():
            for (place_id, costs) in places.items():
                ret_val.set_from_station(int(station_id), int(place_id), float(costs))

        return ret_val
    return o


def load_costs_from_json(f) -> costs_mod.DictCosts:
    """Load costs from a JSON file.

    :param filename: path to the JSON file.
    """
    costs = json.load(f, object_hook=_decode_costs)
    return costs
