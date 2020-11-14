# routr
Proof-of-Concept for Route Risk Profiling

## Quick Setup
1. Clone the repository to a local folder <br/>
```git clone git@github.com:ANALYTQ/routr.git```<br/><br/>
2. Change directory to routr and install dependencies <br/>
```cd routr``` <br/>
```pip install -r requirements.txt```<br/><br/>
3. Set LOCATION_KEY environment variable to contain the API_KEY needed to use Google's Geolocation and Geoencoding Service; grab it from the repo's secrets, or create your own api key (preferred) -- <a href="https://developers.google.com/maps/documentation/javascript/get-api-key">link</a> )<br/>
a. On Linux or Mac<br/>
&nbsp;&nbsp;&nbsp;&nbsp;```export LOCATION_KEY={Google Maps API Key}```<br/>
b. On Windows -- on Command Prompt or PowerShell<br/>
&nbsp;&nbsp;&nbsp;&nbsp;```setx LOCATION_KEY "{Google Maps API Key}"```<br/><br/>
4. Run the app<br/>
```streamlit run app.py```
