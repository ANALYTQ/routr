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
import pandas as pd
import numpy as np
import streamlit as st
import pydeck as pdk


# CREATE FUNCTION FOR MAPS
def create_map(computed_view, layers=[], tooltip=None):
    st.write(pdk.Deck(
        map_style="mapbox://styles/mapbox/streets-v8",
        initial_view_state=computed_view,
        layers=layers,
        tooltip=tooltip,
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


@st.cache(suppress_st_warning=True)
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


@st.cache(suppress_st_warning=True)
def get_location_coordinates(address):
    api_key = os.environ["LOCATION_KEY"]
    get_url = 'https://maps.googleapis.com/maps/api/geocode/json?address=' + address.replace(" ",
                                                                                             "+") + '&key=' + api_key
    r = requests.get(get_url)
    j = json.loads(r.text)
    return tuple([j['results'][0]['geometry']['location']['lat'], j['results'][0]['geometry']['location']['lng']])


@st.cache(suppress_st_warning=True)
def load_accidents_data(file='US_Accidents_June20.csv'):
    return pd.read_csv(file)


# Main Routine
# SET PAGE CONFIG TO WIDE MODE
st.beta_set_page_config(page_title="ROUTR", layout="wide")

# Load acc data on page load
df_acc = load_accidents_data()

# SET PAGE LAYOUT
row1_1, _, row1_3 = st.beta_columns((8, 1, 20))
with row1_1:
    st.title("US Routes Risk Profiling")
    orig = st.text_input("Origin:", "{Current Location}")
    dest = st.text_input("Destination:", "")

with row1_3:
    blue_pin = {
        "url": "https://routr.s3.ap-northeast-2.amazonaws.com/blue_loc_pin.png",
        "width": 242,
        "height": 242,
        "anchorY": 242
    }

    red_pin = {
        "url": "https://routr.s3.ap-northeast-2.amazonaws.com/red_loc_pin.png",
        "width": 242,
        "height": 242,
        "anchorY": 242
    }

    if orig == "{Current Location}":
        midpoint = get_current_location()
        computed = {
            "latitude": midpoint[0],
            "longitude": midpoint[1],
            "zoom": 17,
            "height": 720,
        }

        create_map(computed, layers=[])

    elif orig is not None and orig != "":
        if dest is None or dest == "":
            midpoint = get_location_coordinates(orig)
            computed = {
                "latitude": midpoint[0],
                "longitude": midpoint[1],
                "zoom": 17,
                "height": 720,
            }

            df_icon = pd.DataFrame({"lat": [midpoint[0]],
                                    "lng": [midpoint[1]],
                                    "icon_data": [blue_pin]})

            icon_layer = pdk.Layer(
                type='IconLayer',
                data=df_icon,
                get_icon='icon_data',
                get_size=4,
                size_scale=15,
                get_position=["lng", "lat"]
            )

            create_map(computed, layers=[icon_layer])

        else:
            orig_graph = ox.graph_from_address(orig, network_type='drive_service')
            dest_graph = ox.graph_from_address(dest, network_type='drive_service')
            graph = nx.compose(orig_graph, dest_graph)

            nodes, edges = ox.graph_to_gdfs(graph)

            orig_xy = get_location_coordinates(orig)
            dest_xy = get_location_coordinates(dest)

            orig_node = ox.get_nearest_node(graph, orig_xy, method='euclidean')
            target_node = ox.get_nearest_node(graph, dest_xy, method='euclidean')

            route = nx.shortest_path(G=graph, source=orig_node, target=target_node, weight="length")

            computed = json.loads(pdk.data_utils.compute_view(nodes[['x', 'y']].loc[route]).to_json())
            computed["height"] = 720

            df_icon = pd.DataFrame({"lat": [orig_xy[0], dest_xy[0]],
                                    "lng": [orig_xy[1], dest_xy[1]],
                                    "icon_data": [blue_pin, red_pin]})

            icon_layer = pdk.Layer(
                type='IconLayer',
                data=df_icon,
                get_icon='icon_data',
                get_size=4,
                size_scale=15,
                get_position=["lng", "lat"]
            )

            path = [[nodes['x'].loc[node], nodes['y'].loc[node]] for node in route]
            df_path = pd.DataFrame({"name": [orig.split(",")[0] + " - " + dest.split(",")[0]],
                                    "color": [(255, 0, 0)],
                                    "path": [path]})

            path_layer = pdk.Layer(
                type='PathLayer',
                data=df_path,
                pickable=True,
                get_color='color',
                width_scale=1,
                width_min_pixels=2,
                get_path='path',
                get_width=5
            )

            # Reducing query size of accident data
            min_y = min(nodes['y'])
            max_y = max(nodes['y'])
            min_x = min(nodes['x'])
            max_x = max(nodes['x'])

            mask = ((df_acc['Start_Lat'] >= min_y) & (df_acc['Start_Lat'] <= max_y)
                    & (df_acc['Start_Lng'] >= min_x) & (df_acc['Start_Lng'] <= max_x))

            df_rel_acc = df_acc.loc[mask]

            df_rel_acc['Coordinates'] = [[] for i in range(len(df_rel_acc))]
            for i in df_rel_acc.index:
                df_rel_acc['Coordinates'].loc[i].append(df_rel_acc['Start_Lng'].loc[i])
                df_rel_acc['Coordinates'].loc[i].append(df_rel_acc['Start_Lat'].loc[i])

            rel_cols = ['ID', 'Severity', 'Start_Time', 'Weather_Condition', 'Visibility(mi)', 'Temperature(F)',
                        'Coordinates']
            df_rel_acc = df_rel_acc[rel_cols].replace(np.nan, "Not Available")

            acc_layer = pdk.Layer(
                "ScatterplotLayer",
                df_rel_acc,
                pickable=True,
                opacity=0.5,
                stroked=False,
                filled=True,
                radius_scale=8,
                radius_min_pixels=1,
                radius_max_pixels=100,
                line_width_min_pixels=1,
                get_position="Coordinates",
                get_radius="Severity",
                get_fill_color=[255, 140, 0],
                get_line_color=[0, 0, 0],
            )

            create_map(computed,
                       layers=[icon_layer, path_layer, acc_layer],
                       tooltip={"text": "ID: {ID}\nTimestamp: {Start_Time}\nWeather: {"
                                        "Weather_Condition}\nTemperature(F): {Temperature(F)}\nVisibility(mi): {"
                                        "Visibility(mi)}\nSev: {Severity}"})
