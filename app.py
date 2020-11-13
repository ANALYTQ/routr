# Copyright 2020 ANALYTQ
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import platform
import subprocess
import requests
import json

import osmnx as ox
import networkx as nx
import streamlit as st
import pydeck as pdk


# CREATE FUNCTION FOR MAPS
def create_map(computed_view, layers=[]):
    st.write(pdk.Deck(
        map_style="mapbox://styles/mapbox/streets-v8",
        initial_view_state=computed_view,
        layers=layers,
    ))


def get_mac_aps():
    scan_cmd = subprocess.Popen(['airport', '-s'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    scan_out, scan_err = scan_cmd.communicate()
    aps = []
    scan_out_lines = str(scan_out).split("\\n")[1:-1]
    for line in scan_out_lines:
        clean = [e for e in line.split(" ") if e != ""]
        bssid = [e for e in clean if ":" in e][0]
        strength = int(clean[clean.index(bssid) + 1])
        aps.append((bssid, strength))

    return aps


def get_current_location():
    data_dict = {
        "considerIp": "true",
        "wifiAccessPoints": []
    }

    # Specific to MacOS
    if "macOS" in platform.platform():
        aps = get_mac_aps()
        for ap in aps:
            data_dict["wifiAccessPoints"].append({
                "macAddress": ap[0],
                "signalStrength": ap[1]
            })

    api_key = os.environ["LOCATION_KEY"]
    post_url = 'https://www.googleapis.com/geolocation/v1/geolocate?key=' + api_key
    r = requests.post(post_url, data=json.dumps(data_dict))
    j = json.loads(r.text)
    return tuple([j['location']['lat'], j['location']['lng']])


def get_location_coordinates(address):
    api_key = os.environ["LOCATION_KEY"]
    get_url = 'https://maps.googleapis.com/maps/api/geocode/json?address=' + address.replace(" ",
                                                                                             "+") + '&key=' + api_key
    r = requests.get(get_url)
    j = json.loads(r.text)
    return tuple([j['results'][0]['geometry']['location']['lat'], j['results'][0]['geometry']['location']['lng']])


# Main Routine
# SET PAGE CONFIG TO WIDE MODE
st.beta_set_page_config(page_title="ROUTR", layout="wide")

# SET PAGE LAYOUT
row1_1, _, row1_3 = st.beta_columns((8, 1, 20))
with row1_1:
    st.title("US Routes Risk Profiling")
    orig = st.text_input("Origin:", "{Current Location}")
    dest = st.text_input("Destination:", "")

with row1_3:
    if orig == "{Current Location}":
        midpoint = get_current_location()
        computed = {
            "latitude": midpoint[0],
            "longitude": midpoint[1],
            "zoom": 17,
            "height": 720,
        }
        create_map(computed)

    elif orig is not None and orig != "":
        if dest is None or dest == "":
            midpoint = get_location_coordinates(orig)
            computed = {
                "latitude": midpoint[0],
                "longitude": midpoint[1],
                "zoom": 17,
                "height": 720,
            }
            create_map(computed)

        else:
            places = [orig] + [dest]

            graph = ox.graph_from_address(places, network_type='drive_service')
            nodes, edges = ox.graph_to_gdfs(graph)

            orig_xy = get_location_coordinates(orig)
            dest_xy = get_location_coordinates(dest)

            orig_node = ox.get_nearest_node(graph, orig_xy, method='euclidean')
            target_node = ox.get_nearest_node(graph, dest_xy, method='euclidean')

            route = nx.shortest_path(G=graph, source=orig_node, target=target_node, weight="length")

            computed = json.loads(pdk.data_utils.compute_view(nodes[['x', 'y']].loc[route]).to_json())
            computed["height"] = 720

            create_map(computed)
