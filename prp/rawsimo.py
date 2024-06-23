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

"""
Convert rawsimo files to PRP JSON files.

.. moduleauthor:: Ruslan Krenzler

18 Januar 2019
"""

import math
import xml.etree.ElementTree as ET
import networkx as nx
import networkx.algorithms.shortest_paths as shortest_paths
import prp.core.warehouse as system_mod
import prp.core.objects as objects
import prp.core.costs as costs_mod
import prp.xy as xy


class LayoutGrpah:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.positions = {}
        self.station_nodes = []  # All waypoints witch belong to the output station.
        self.place_nodes = []  # All waipoints which may have a pod.
        self.pods = {}  # Positions of all pods.
        # Run calculate_distances to initialize station_to_place and place_to_station.
        self.station_to_place = None
        self.place_to_station = None
        self.xml_tree = None
        # The dictionaries below are used to translate waypoints to warehouse game station ids
        # and warehouse game place ids.

        self.node_to_place = {}
        self.node_to_station = {}
    def load_from_xml(self, filename):
        self.xml_tree = ET.parse(filename)
        root = self.xml_tree.getroot()
        waypoints = next(root.iter("Waypoints"))
        # Add Nodes to a graph.
        self.positions = {}
        self.gvz_scale = 1.0  # Scale factor for GraphViz

        current_wg_place = 1 # The place id for warehouse game. It startes with 1.

        for waypoint in waypoints:
            x = float(waypoint.attrib["X"])
            y = float(waypoint.attrib["Y"])
            ID = int(waypoint.attrib["ID"])
            station_ID = int(waypoint.attrib["OutputStation"])
            if station_ID >= 0:
                self.station_nodes.append(ID)
                # Add mapping rawsimi->warehouse game for stations. In rawsim the stations have
                # ids 0, 1, 2,... in warehouse game the station ids are 1, 3, 3,...
                self.node_to_station[ID] = station_ID + 1

            if waypoint.attrib["PodStorageLocation"]=="true":
                self.place_nodes.append(ID)
                self.node_to_place[ID] = current_wg_place
                current_wg_place += 1
            self.positions[ID] = (x, y)
            # Add position in graph viz format
            may_have_pods = waypoint.attrib["PodStorageLocation"]=="true"
            pod_id = int(waypoint.attrib["Pod"])
            self.graph.add_node(ID, x=x, y=y, may_have_pods=may_have_pods, pod_id=pod_id)
            if pod_id >= 0:
                self.pods[pod_id] = ID
        # Add edges.
        for waypoint in waypoints:
            from_ID = int(waypoint.attrib["ID"])
            paths = next(waypoint.iter("Paths"))
            # Read adjacent nodes.
            previous = from_ID
            for neigbour in paths:
                if neigbour.tag == "Waypoint":
                    to_ID = int(neigbour.text)
                    # Calculate distance
                    d = self.edge_distance(from_ID, to_ID)
                    self.graph.add_edge(from_ID, to_ID, d=d)
        self.update_graph_viz()

    def is_place(self, node_id):
        """Return true if the graph node is a place.

        Place means that the corresponding node (waipoint in rawsimo) may carry place.
        """
        return self.graph.nodes[node_id]["may_have_pods"]

    def is_station(self, node_id):
        return node_id in self.station_nodes

    def edge_distance(self, i, j):
        x_diff = self.graph.nodes[i]["x"] - self.graph.nodes[j]["x"]
        y_diff = self.graph.nodes[i]["y"] - self.graph.nodes[j]["y"]
        return math.sqrt(x_diff**2+y_diff**2)

    def distance_graph_from_station(self):
        """Return distance graph from stations to places.

        We consider that robots with pods cannot cross places with other pods. That is why all nodes
        in the path which can carry pods could not be crossed. But the very last node must be able to
        carry pods. To prevent this crossing we return a graph where places with pods are only
        destinations but never the sources.
        """
        g = nx.DiGraph()
        g.add_nodes_from(self.graph)
        # Add edges
        for (edge_id, v) in self.graph.edges().items():
            if not self.is_place(edge_id[0]):
                g.add_edge(edge_id[0], edge_id[1], weight=v["d"])

        return g

    def distance_graph_to_station(self):
        """Return distance graph from places to stations.

        We consider that robots with pods cannot cross places with other pods. That is why all nodes
        in the path which can carry pods could not be crossed. But the very last node must be able to
        carry pods. To prevent this crossing we return a graph where places with pods are only
        sources but never destinations.
        """
        g = nx.DiGraph()
        g.add_nodes_from(self.graph)
        # Add edges
        for (edge_id, v) in self.graph.edges().items():
            if not self.is_place(edge_id[1]):
                g.add_edge(edge_id[0], edge_id[1], weight=v["d"])

        return g

    def update_graph_viz(self):
        # Update graphiv attributes
        for (node_id, v) in self.graph.nodes().items():
            # Add position in graph viz format
            gvz_pos = "{},{}!".format(self.gvz_scale*v["x"],self.gvz_scale*v["y"])
            self.graph.nodes[node_id]["pos"] = gvz_pos
            # If it may have pods mark it yellow
            if v["may_have_pods"]:
                self.graph.nodes[node_id]["style"] = "filled"
                self.graph.nodes[node_id]["fillcolor"] = "yellow"
            if node_id in self.station_nodes:
                self.graph.nodes[node_id]["style"] = "filled"
                self.graph.nodes[node_id]["fillcolor"] = "green"

    def update_heatmap_graph_viz(self, map):
        min_val = min(map.values())
        max_val = max(map.values())

        for (node_id, v) in self.graph.nodes().items():
            if node_id in map.keys():
                self.graph.nodes[node_id]["style"] = "filled"
                color_index = round(9-(map[node_id]-min_val)/(max_val-min_val)*8)
                self.graph.nodes[node_id]["fillcolor"] = "/blues9/{}".format(color_index)
                self.graph.nodes[node_id]["label"]="{}({})".format(node_id, map[node_id])
            else:
                try:
                    del self.graph.nodes[node_id]["fillcolor"]
                except:
                    pass

    def distances_from_station(self):
        """Return a table with distances from station to places.

        The table is a nested dictionary with station waypoint -> place waypoint -> distance.
        """
        #
        g = self.distance_graph_from_station()
        all_distances = shortest_paths.all_pairs_dijkstra_path_length(g)
        # Look only at stations
        from_station_distances = {}
        for (from_node_id, from_distances) in all_distances:
            # Focus only on stations.
            if self.is_station(from_node_id):
                to_place_distances = {}
                for (dest_wp_id, length) in from_distances.items():
                    # Focus only on places.
                    if self.is_place(dest_wp_id):
                        to_place_distances[dest_wp_id] = length

                from_station_distances[from_node_id] = to_place_distances
        return from_station_distances

    def distances_to_station(self):
        """Return a table with distances from places to stations.

        The table is a nested dictionary with place waypoint ->station waypoint -> distance.
        """
        # get
        g = self.distance_graph_to_station()
        all_distances = shortest_paths.all_pairs_dijkstra_path_length(g)
        # Look only at stations
        from_places_distances = {}
        for (from_node_id, from_distances) in all_distances:
            # Focus only on places.
            if self.is_place(from_node_id):
                to_station_distances = {}
                for (dest_wp_id, length) in from_distances.items():
                    # Focus only on stations.
                    if self.is_station(dest_wp_id):
                        to_station_distances[dest_wp_id] = length

                        from_places_distances[from_node_id] = to_station_distances
        return from_places_distances


    def calculate_distances(self):
        self.station_to_place = self.distances_from_station()
        self.place_to_station = self.distances_to_station()

    def store_distances_to_csv(self, filename):
        """Store distances into a CSV file."""
        # Joint to a table
        table = []
        for (from_node, to_nodes) in self.station_to_place.items():
            for (to_node, distance) in to_nodes.items():
                row = {}
                row["StationNode"] = from_node
                row["PlaceNode"] = to_node
                row["FromStationDistance"] = distance
                row["ToStationDistance"] = self.place_to_station[to_node][from_node]
                table.append(row)

        with open(filename, "w") as csvfile:
            fieldnames = ["StationNode", "PlaceNode", "FromStationDistance", "ToStationDistance"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, lineterminator='\n')
            writer.writeheader()
            writer.writerows(table)
            csvfile.close()

    def load_distances_from_csv(self, filename):
        self.station_to_place = {}
        self.place_to_station = {}
        with open(filename, "r") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Add station if not already exists
                station_id = int(row["StationNode"])
                place_id = int(row["PlaceNode"])
                if station_id not in self.station_to_place.keys():
                    self.station_to_place[station_id] = {}
                self.station_to_place[station_id][place_id] = float(row["FromStationDistance"])
                if place_id not in self.place_to_station.keys():
                    self.place_to_station[place_id] = {}
                self.place_to_station[place_id][station_id] = float(row["ToStationDistance"])
            csvfile.close()

    def average_distance(self, place_node, weights):
        result = 0
        for station_node, weight in weights.items():
            result+= weight*(self.station_to_place[station_node][place_node] + self.place_to_station[place_node][station_node])
        return result

    def uniform_station_weights(self):
        """Return uniformly distributed station weights."""
        w = {}
        for node in self.station_nodes:
            w[node] = 1/len(self.station_nodes)

        return w

    def get_average_distances(self):
        """Return average distances of all places.

        This function assume uniform station weights.
        """
        w = self.uniform_station_weights()
        table = {}
        for place_id in self.place_nodes:
            table[place_id] = self.average_distance(place_id, w)

        return table

    def get_empty_warehouse(self, station_max_n) -> system_mod.Warehouse:
        # Create a mapping from waypoints to warehouse places.
        nstations = len(self.station_nodes)
        # Create a mapping from waypoints to warehouse stations.
        """Return empty system."""
        system = system_mod.Warehouse()
        # If stantion_max_n is not a dictionary expand it to dictionary.
        if type(station_max_n) != dict:
            station_max_n = dict(zip(self.node_to_station.values(), [station_max_n]*nstations))
        # Add empty stations first.
        for station_id in self.node_to_station.values():
            system.add_station(objects.Station(station_id, station_max_n[station_id]))
        # Add places.
        nplaces = len(self.place_nodes)
        system.set_num_places(nplaces)
        # Add pods
        npods = len(self.pods)
        system.set_num_pods(npods)
        return system

    def get_costs(self):
        """Return costs which are distances between places and stations.

        The to station costs is Manhattan distance to station tail + the lengths of the station.
        From station costs are costs from the station head.
        """
        ret_val = costs_mod.DictCosts()
        # Set functions' domain.
        ret_val.set_num_stations(len(self.station_nodes))
        ret_val.set_num_places(len(self.place_nodes))

        # Fill the mapping of from station costs.
        for (station_id, places) in self.station_to_place.items():
            for (place_id, distance) in places.items():
                ret_val.set_from_station(self.node_to_station[station_id],
                                         self.node_to_place[place_id], distance)

        for (place_id, stations) in self.place_to_station.items():
            for (station_id, distance) in stations.items():
                ret_val.set_to_station(self.node_to_place[place_id],
                                       self.node_to_station[station_id], distance)

        return ret_val

    def get_warehouse(self, station_max_n) -> system_mod.Warehouse:
        warehouse = self.get_empty_warehouse(station_max_n)
        # Store inital state.
        self.set_initial_state(warehouse)
        # calculate distances. This may take time.
        self.calculate_distances()
        # add costs.
        warehouse.costs = self.get_costs()
        return warehouse

    def set_initial_state(self, system: system_mod.Warehouse):
        """Set initial state of the system."""
        # Empty stations.
        for station_id, station in system.stations.items():
            station.state = []

        # Assign pods to places
        for rawsim_pod_id, node_id in self.pods.items():
            pod_id = rawsim_pod_id + 1 # Convert in warehouse game pod ID 1, 2, 3, ...
            place_id = self.node_to_place[node_id] # Convert in warehouse game place ID 1, 2,...
            system.assign_pod_to_place(pod_id, place_id)


    def modify_layout_xml(self, place_to_pod, filename):
        root = self.xml_tree.getroot()
        #self.xml_tree.write(USORTED_REFERENCE_LAYOUT_XML_FILE) # For debugging.
        waypoints = next(root.iter("Waypoints"))
        for waypoint in waypoints:
            ID = int(waypoint.attrib["ID"])
            if ID in self.place_nodes:
                if ID in place_to_pod.keys():
                    waypoint.attrib["Pod"] = str(place_to_pod[ID])
                else:
                    waypoint.attrib["Pod"] = str(-1)

        # The pods have coordinates. They must be consistent with new places to.
        # We adjust the coordinates according to the mapping of place_to_pod.
        # Convert inverse mapping of busy places for faster access to the place coordinates.
        pod_to_place = {}
        for place_node_id, pod_id in place_to_pod.items():
            if pod_id >= 0:
                pod_to_place[pod_id] = place_node_id

        pods = next(root.iter("Pods"))
        for pod in pods:
            pod_id = int(pod.attrib["ID"])
            place_node_id = pod_to_place[pod_id]
            x = self.graph.nodes[place_node_id]["x"]
            y = self.graph.nodes[place_node_id]["y"]
            pod.attrib["X"] = str(x)
            pod.attrib["Y"] = str(y)

        self.xml_tree.write(filename)

    def get_xy_layout(self, stations):
        """

        :param stations: List of XYStations. The station will be moved in such a way. That its
        queue-head overlaps with the corresponding rawsim station. If the station id is a
        then the correspong rawsmo station id is a-1
        :return: XYLayout
        """
        layout = xy.Layout()

        # calculate world area
        all_x = []
        all_y = []

        for node_args in self.graph.nodes.values():
            all_x.append(node_args["x"])
            all_y.append(node_args["y"])

        station_to_node = dict(zip(self.node_to_station.values(), self.node_to_station.keys()))
        # Add stations.
        for station in stations:
            # Find corresponding station in rawsim.
            node_id = station_to_node[station.id]
            x = self.graph.nodes[node_id]["x"]
            y = self.graph.nodes[node_id]["y"]

            # Put the head on the xy-coordinate in the graph. Adjust all other segments
            x_correction = x - station.segments[0].x
            y_correction = y - station.segments[0].y
            corrected_segments =[]
            for segment in station.segments:
                corrected_segments.append(xy.Coord(segment.x+x_correction, segment.y+y_correction))
            corrected_station = xy.XYStation(station.id, segments=corrected_segments)
            layout.add_station(corrected_station)

        # Add places to layout.
        for node_id in self.place_nodes:
            # Translate graphs waypoint ids to warehouse game place ids.
            place_id = self.node_to_place[node_id]
            # Get position data from node attributes.
            attr = self.graph.nodes[node_id]
            place = xy.XYPlace(place_id, xy.Coord(attr["x"], attr["y"]))
            layout.add_place(place)

        return layout