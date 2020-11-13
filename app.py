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

import streamlit as st
import pydeck as pdk


# CREATE FUNCTION FOR MAPS
def create_map(lat, lon, zoom):
    st.write(pdk.Deck(
        map_style="mapbox://styles/mapbox/streets-v8",
        initial_view_state={
            "latitude": lat,
            "longitude": lon,
            "zoom": zoom,
            "height": 720,
            # "pitch": 50,
        },
        layers=[],
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
    return [j['location']['lat'], j['location']['lng']]


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
    midpoint = get_current_location()
    create_map(midpoint[0], midpoint[1], 16)
