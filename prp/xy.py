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
"""Implement objects of the simulation on a xy-plane with manhattan metric.

.. moduleauthor:: Ruslan Krenzler

25 November 2017
"""

import copy
from collections import namedtuple
import json
import numpy
from prp.core.objects import Station
import prp.core.objects as objects
import prp.core.warehouse as system_mod
import prp.core.costs as costs

# class Coord(namedtuple('Coord', ['x', 'y'], defaults=[0, 0])): # Default arguments require python 3.7


class Coord(namedtuple('Coord', ['x', 'y'])):
    """Cartesian (x,y) coordinates."""

    def distance(self, other):
        """Calculate manhattan distance to the other ordinates.

        :param other: Other coordinates.
        :return: manhattan distance to the between this and the other coordinates.
        """
        return abs(self.x - other.x) + abs(self.y - other.y)


class XYPlace:
    """A place which is bound to cartesian coordinates on the xy-plane.

    We do not use named tuple because json cannot recognize them properly.
    """

    def __init__(self, id: int, coord: Coord):
        """Create a place with xy-coordinates."""
        self.id = id
        self.coord = coord


class XYStorageArea:
    """Create storage area between points bottmo_left = (x1,y1) and top_right = (x2,y2).

    Fill this area with places by rows. Use discrete size of the place = 1.
    The bottom_left point is included in the area, the top_right point is excluded.
    """

    def __init__(self, p1: Coord, p2: Coord, from_id=1, by=1):
        """Create rectangular stoarage area filled with places.

        :param p1: One point of the rectangular area.
        :param p2: Other point ofthe recgangular area.
        :param begin_id: The id of the first place, other ids are made by increament:
            from_id+by, from_id+2*by, ...
        """
        self.places = {}
        id = from_id
        for y in range(p1.y, p2.y):
            for x in range(p1.x, p2.x):
                self.places[id] = XYPlace(id, Coord(x, y))
                id = id + by


class XYStation(Station):
    """A station on the xy-plane with given coordinates of the places or of the tail and of the head."""

    def __init__(self, id, segments: list=None, hcoord: Coord=None, tcoord: Coord=None, step: float = 1):
        """Create a station with given head and tail coordinates.

        :param segments: list of coordinates of the queue segments. The 0-th element is the queue head.
        :param hcoord: xy-coordinates of the queue head at this station.
        :param tcoord: xy-coordinates of the queue tail at this station.
        :param step: size of the place in the station as an abolute value

        Note: an xy station is created differently from an xy storage area. The area which
        contains the station includes both points. In Constrast the Storage area includes
        only the bottom left point.
        """
        if segments is not None:
            self.segments = segments
        else:
            self.segments = self._calc_segment_coordinates(hcoord, tcoord, step)

        super(XYStation, self).__init__(id, len(self.segments))

    @staticmethod
    def _calc_segment_coordinates(hcoord: Coord, tcoord:  Coord, step: float):
        """Calculate coordinates of the queue elements."""
        coords = []
        # Include coordinates of the tail.
        x_step = step
        if hcoord.x > tcoord.x:
            x_step = - x_step
        y_step = step
        if hcoord.y > tcoord.y:
            y_step = -y_step

        for x in numpy.arange(hcoord.x, tcoord.x + x_step / 2, x_step):
            for y in numpy.arange(hcoord.y, tcoord.y + y_step / 2, y_step):
                coords.append(Coord(x, y))
        return coords

    def get_pod_coordinates(self, pod_id):
        """Get coordinates of the pod in the station.

        The coordinates are counted from the head.
        That means: if here is only one pod in the queue
        it has coordinates of the queue head.

        :param pod_id: id of the pod.
        :return: coordinates of the pod or None if pod with id pod_id was not found.
        """
        try:
            index = self.state.index[pod_id]
            return self.segments[index]
        except ValueError as e:
            return None

    def get_segment_coordinates(self, index):
        """Get coordinates of a queue element.

        :param index: must between 0 and maximal queue length - 1,
            index = 0 points to the queue head.
        """
        return self.segments[index]


class XYWorld:
    """Define 2D rectangular area for the problem.

    We assume that the bottom left corner has coordinates (0,0).
    """

    def __init__(self, bottom_left, top_right):
        """Create a world between two points.

        Both points are included in the area.
        """
        self.bottom_left = bottom_left
        self.top_right = top_right

        self.width = top_right.x - bottom_left.x
        self.height = top_right.y - bottom_left.y
    # Pygame coordinates: (0,0) are upper left coordinates.


class ScreenConverter:
    """Convert world coordinates to screen coordinates."""

    def __init__(self, world: XYWorld):
        self.world = world

    def set_screen_corrdinates(self, x1, y1, x2, y2):
        self.screen_x1 = x1
        self.screen_y1 = y1
        self.screen_x1 = x2
        self.screen_x2 = y2

        # See https://de.wikipedia.org/wiki/Affine_Abbildung.
        # Create transformation matrix. it must hold
        # A*t(width,0) = t(x2-x1,0)
        # A*t(0,height)= t(0,-(y2-y1))
        # A = [[ (x2-x1)/self.width, 0],
        #     [ 0, -(y2-y1)/self.height]]
        # The matrix with translation is then
        # [[A, t],
        #  [o  1]]
        # First set t = (0,0)
        self.WS = numpy.matrix([[(x2 - x1) / self.world.width, 0, 0],
                                [0, -(y2 - y1) / self.world.height, 0],
                                [0, 0, 1]])
        # Then correct t in such a way, that the center of the world
        # and the center of the screen coincide.
        wcx = (self.world.bottom_left.x + self.world.top_right.x) / 2
        wcy = (self.world.bottom_left.y + self.world.top_right.y) / 2
        scx = (x1 + x2) / 2
        scy = (y1 + y2) / 2
        uncoreccted_screen_center = self.world_to_screen(wcx, wcy)
        # Now calculate traslation
        tx = scx - uncoreccted_screen_center[0]
        ty = scy - uncoreccted_screen_center[1]
        # Insert (tx,ty) into WS
        self.WS[0, 2] = tx
        self.WS[1, 2] = ty

    def world_two_screen(self, coord: Coord):
        """Convert world coordinates to screen coordinates with (0,0) on top left."""
        v = numpy.matrix([[coord.x], [coord.y], [1]])
        w = self.WS * v
        return (w[0, 0], w[1, 0])

        # left top, width height
    def world_to_screen_rect(self, lb, w, h):
        """Convert rectangular in world to a rectangular on the screen.

        :param lb: Left bottom point of the rectangular in the xy-world.
        :param w: width of the rectangle in world units.
        :param l: length of the rectangle in world units.
        """
        (x1, y1) = self.world_2_Screen(lb.x, lb.y)
        (x2, y2) = self.world_2_screen(lb.x + w, lb.y + h)
        return (x1, y1, abs(x2 - x1), abs(y2 - y1))


class Layout:
    """Store and and load places, pods and station.

    This class stores a lot of data as dictionary to make it easy to serialize by JSON.
    """

    def __init__(self):
        self.places = {}
        self.stations = {}

    def add_place(self, place: XYPlace):
        """Add a place to layoutout"""
        self.places[place.id] = place

    def add_station(self, station: XYStation):
        """Add a station to layout."""
        self.stations[station.id] = station

    def get_costs(self):
        """Return costs which are distances between places and stations.

        The to station costs is Manhattan distance to station tail + the lengths of the station.
        From station costs are costs from the station head.
        """
        ret_val = costs.DictCosts()
        # Set functions' domain.
        ret_val._station_ids = copy.copy(list(self.stations.keys()))
        ret_val._place_ids = copy.copy(list(self.places.keys()))
        # Fill the mapping of from station costs.
        for (station_id, station) in self.stations.items():
            from_coord = station.segments[0]
            ret_val.from_station_dict[station_id] = {}
            for (place_id, place) in self.places.items():
                d = from_coord.distance(place.coord)
                ret_val.from_station_dict[station_id][place_id] = d
        # Fill the mapping from place to stations.
        for (place_id, place) in self.places.items():
            ret_val.to_station_dict[place_id] = {}
            for (station_id, station) in self.stations.items():
                d = place.coord.distance(station.segments[-1])
                additional_d = station.max_n - 1
                ret_val.to_station_dict[place_id][station_id] = d + additional_d
        ret_val.num_places = len(self.places)
        ret_val.num_stations = len(self.stations)

        return ret_val

    def store_to_json(self, f):
        """Store data to file in JSON format."""
        json.dump(self, f, cls=LayoutEncoder)

    def load_from_json(self, f):
        """Load content from JSON format."""
        tmp_layout = json.load(f, object_hook=decode_layout)
        self.places = tmp_layout.places
        self.stations = tmp_layout.stations

    def get_empty_warehouse(self) -> system_mod.Warehouse:
        """Return empty system."""
        system = system_mod.Warehouse()
        # Add empty stations first.
        for (station_id, xy_station) in self.stations.items():
            system.add_station(objects.Station(station_id, xy_station.max_n))
        # Add places.
        system.set_num_places(max(self.places.keys()))
        return system


class LayoutEncoder(json.JSONEncoder):
    """This class helps to convert layout to and from json format."""

    KEY_PLACE_COORDS = "Places"
    KEY_OUTPUT_STATION_COORDS = "OutputStations"

    """This file is used to incode coordinate objects"""

    def default(self, o):
        """Convert xy objects to dictionary."""
        # if isinstance(o, Coord): # this does not work
        #    return {"x": o.x, "y": o.y}
        if isinstance(o, XYPlace):
            return {"X": o.coord.x, "Y": o.coord.y}
        elif isinstance(o, XYStation):
            segments = []
            for coord in o.segments:
                segments.append({"X": coord.x, "Y": coord.y})
#            return {Layout.KEY_WORD_SEGMENTS: segments }
            return segments
        elif isinstance(o, Layout):
            return {self.KEY_PLACE_COORDS: o.places,
                    self.KEY_OUTPUT_STATION_COORDS: o.stations}
        return {'__{}__'.format(o.__class__.__name__): o.__dict__}


def decode_layout(o):
    """This function helps to convert JSON data to a layout."""
    layout = Layout()
    root_node = False

    if LayoutEncoder.KEY_PLACE_COORDS in o:
        root_node = True
        src = o[LayoutEncoder.KEY_PLACE_COORDS]
        for (id, val) in src.items():
            # Convert id to integer. JSON stores it as string.
            layout.places[int(id)] = XYPlace(int(id), val)

    if LayoutEncoder.KEY_OUTPUT_STATION_COORDS in o:
        root_node = True
        src = o[LayoutEncoder.KEY_OUTPUT_STATION_COORDS]
        for (id, segments) in src.items():
            # Convert id to integer. JSON stores it as string.
            layout.stations[int(id)] = XYStation(int(id), segments)

    if "X" in o and "Y" in o:
        return Coord(o["X"], o["Y"])

    if root_node:
        return layout
    return o
