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
""" Create a test instance with 504 places, 441 pods, two stations with queue of the length 6 and 4,
from RAWSim-O files.
.. moduleauthor:: Ruslan Krenzler

17 Juli 2018
"""
import sys
sys.path.append('../')  # noqa: E402
import prp.recorder as recorder
import prp.xy as xy
import prp.utils as utils
import prp.rawsimo as rawsimo


# Input paths.
LAYOUT_XML_FILE = "../data/rawsimo/1-1-2-10-441-b-slow-pick-cap-20.xinst"

# Where to store resulting files.
LAYOUT_FILE = "../data/504-layout.json"
INITIAL_STATE_FILE = "../data/504-initial-state.json"
COSTS_FILE = "../data/504-costs.json"

NQ1 = 6  # Maximal queue length at the station 1.
NQ2 = 4  # Maximal queue length at the station 2.

# Load RAWSim-O layout.
lg = rawsimo.LayoutGrpah()
lg.load_from_xml(LAYOUT_XML_FILE)

warehouse = lg.get_warehouse({1: NQ1, 2: NQ2})

print("Store initial state...")
utils.create_missing_directories_of_file(INITIAL_STATE_FILE)
with open(INITIAL_STATE_FILE, 'w') as outfile:
    recorder.store_initial_state_to_json(warehouse, outfile)
print("Initial state stored.")

print("Store costs...")
utils.create_missing_directories_of_file(COSTS_FILE)
with open(COSTS_FILE, 'w') as outfile:
    recorder.store_costs_to_json(warehouse.costs, outfile)
print("Costs stored.")

# Create layout.
print("Creating layout...")
# Add stations. They station will be moved on the layout in such a way, that its head has the same position as the
# the station in RAWSim-O files.
station1 = xy.XYStation(1, hcoord=xy.Coord(0, 0), tcoord=xy.Coord(0, NQ1 - 1))
station2 = xy.XYStation(2, hcoord=xy.Coord(0, 0), tcoord=xy.Coord(0, -NQ2 + 1))
layout = lg.get_xy_layout([station1, station2])
# Store layout to files.
utils.create_missing_directories_of_file(LAYOUT_FILE)
with open(LAYOUT_FILE, 'w') as outfile:
    layout.store_to_json(outfile)
print("Layout created.")