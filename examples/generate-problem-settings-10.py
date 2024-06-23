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
""" Create a test instance with 10 places, 10 pods, two stations with queue of the length 3 and 1000 pod departures.

                     | | | | station 1

|10|9|8|7|6|5|4|3|2|1|

                     | | | | station 2

.. moduleauthor:: Ruslan Krenzler

17 Juli 2018
"""
import sys
sys.path.append('../')  # noqa: E402
import numpy.random
import prp.core.departure_generators as departure_generators
import prp.solvers.simple as simple_solvers
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils


# Where to store resulting files.
LAYOUT_FILE = "../data/10-layout.json"
INITIAL_STATE_FILE = "../data/10-initial-state.json"
COSTS_FILE = "../data/10-costs.json"
DEPARTURES_FILE = "../data/10-departures.json"

NPLACES = 10  # Number of places
NPODS = 10  # Number of pods.
NQ = 3  # Queue length.

MAX_TIME = 1000  # Number of steps the system is running.
MAX_WEIGHT_RATIO = 20  # Weights ratio between the most frequent and less frequent pod.
STATION_WEIGHTS = {1: 0.5, 2: 0.5}  # Probability for a pod to departure to a particular station.

# The random task generators use numpy random. To have reproducible results we set the seed to a fixed value.
# Generate data, where the frequencies of the pods is ordered by their weights.
numpy.random.seed(3)

#  -- Create a layout with storage in the middle and two stations on the right side. --
# The very left place has coordinate (0,0).
layout = xy.Layout()
storage_length = NPLACES

# Add Storage places to layout. Such that the last place get coordinate 0,0
for place in range(1, NPLACES + 1):
    xy_place = xy.XYPlace(place, xy.Coord(NPLACES - place, 0))
    layout.add_place(xy_place)

# Create a station 1 and put it on the upper right of the storage area.
station1 = xy.XYStation(1, hcoord=xy.Coord(storage_length + NQ - 1, 2),
                        tcoord=xy.Coord(storage_length, 2))
station2 = xy.XYStation(2, hcoord=xy.Coord(storage_length + NQ - 1, -2),
                        tcoord=xy.Coord(storage_length, -2))
layout.add_station(station1)
layout.add_station(station2)

# -- Add pods to the warehouse --
warehouse = layout.get_empty_warehouse()
# Bind costs to the warehouse.
warehouse.set_costs(layout.get_costs())

# Add pods to the warehouse..
# Give to the pods the same id as to the places.
warehouse.set_num_pods(NPODS)
for place in warehouse.places:
    warehouse.assign_pod_to_place(place, place)

#Calculate weights of the pods, such that the ratio between the most and the least frequent pods is MAX_WEIGHT_RATIO.
pod_w = departure_generators.get_geometric_weights(npods=NPODS, max_weight_ratio=MAX_WEIGHT_RATIO)
# Use equal station weights.
generator = departure_generators.MarkovianGenerator(warehouse,
                                                    pod_w, STATION_WEIGHTS,
                                                    MAX_TIME)
departure_recorder = recorder.DepartureRecorder(generator)
warehouse.set_departure_generator(departure_recorder)

# Create and store layout.
utils.create_missing_directories_of_file(LAYOUT_FILE)
with open(LAYOUT_FILE, 'w') as outfile:
    layout.store_to_json(outfile)

# Use layout data to create costs based on manhattan metric and storing them to a JSON file.
costs = layout.get_costs()
utils.create_missing_directories_of_file(COSTS_FILE)
with open(COSTS_FILE, 'w') as outfile:
    recorder.store_costs_to_json(costs, outfile)

# Store the initial system state.
utils.create_missing_directories_of_file(INITIAL_STATE_FILE)
with open(INITIAL_STATE_FILE, 'w') as outfile:
    recorder.store_initial_state_to_json(warehouse, outfile)

# Use some solver to keep the system running. For the MarkovianGenerator the solver is not important.
# The only important property of the solver is -- it must be fast.
solver = simple_solvers.SomePlaceSolver(warehouse)

# Run the system until no departure left.
while not warehouse.finished():
    place_id = solver.decide_new_place()
    warehouse.next(place_id)

# Store departures.
utils.create_missing_directories_of_file(DEPARTURES_FILE)
with open(DEPARTURES_FILE, 'w') as outfile:
    departure_recorder.store_to_json(outfile)
