# to run locally: go to app folder and: streamlit run dewpoint_app.py
# for https: also run:  ngrok http 8501

# This Streamlit app helps you decide whether to run HRV, based on indoor and outdoor temp and humidity.
# It calculates the dew point for both indoor and outdoor and displays them in a heatmap.
# It provides a suggestion for HRV homeowners, based on the difference between the indoor and outdoor dew points.
# It also uses the OpenWeatherMap API to get the forecast for +6h and +12h.

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import os
from dotenv import load_dotenv
import pytz
from datetime import datetime, timezone, timedelta
from dewpoint_weather import (
    get_weather,
    calculate_dew_point,
    fetch_weather_by_gps,
    reverse_geocode,
    get_js_geolocation,
    temperatures,
    humidities,
    dew_points,
    text_labels,
)
from beach_weather import fetch_estonian_beach_temps, find_nearest_station
from timezonefinder import TimezoneFinder

# ---------------------------------------------------------------------------
# Load API key from .env file
# ---------------------------------------------------------------------------
load_dotenv()

# Try Streamlit secrets first, then environment variable (for local .env)
OPENWEATHER_API_KEY = st.secrets.get("OPENWEATHER_API_KEY") or os.getenv(
    "OPENWEATHER_API_KEY"
)
if not OPENWEATHER_API_KEY:
    st.warning(
        "OpenWeatherMap API key not found. Please add OPENWEATHER_API_KEY to your .streamlit/secrets.toml file."
    )


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 0.2rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# --- Outdoor weather fetch ---
# Try to get user location via JS eval
loc = get_js_geolocation()
# st.write(
#    f"DEBUG: js geolocation returned: {loc}"
# )   Show raw geolocation result for debugging
use_gps = False
location_name = None
if loc and loc.get("latitude") and loc.get("longitude"):
    lat = loc["latitude"]
    lon = loc["longitude"]
    location_name = reverse_geocode(lat, lon)
    #    if location_name:
    #        st.success(f"Detected location: {location_name}")
    #    else:
    #        st.success(f"Detected location: {lat:.4f}, {lon:.4f}")
    use_gps = True
elif loc and loc.get("error"):
    st.warning(f"Geolocation error: {loc['error']}")
# else:
#    st.info(
#        "Allow location access to auto-detect your weather, or enter a city name below."
#    )

# Show detected location
if location_name:
    st.markdown(
        f"<div style='text-align:center; color:gray; font-size:0.95em; margin-top:2em;'>Detected location: "
        f"{location_name}</div>",
        unsafe_allow_html=True,
    )
elif use_gps:
    st.markdown(
        f"<div style='text-align:center; color:gray; font-size:0.95em; margin-top:2em;'>Detected location: "
        f"{lat:.4f}, {lon:.4f}</div>",
        unsafe_allow_html=True,
    )

# Set city input default to empty if location is detected, otherwise use a default city
city_default = "" if use_gps else "Viimsi"
city = st.text_input(
    "City name for outdoor weather (override GPS location)", value=city_default
)

# Add at the top, after imports:
FORECAST_HOUR_1 = 3
FORECAST_HOUR_2 = 7

# Replace the session_state initialization block with:
if "forecast_hour_1" not in st.session_state:
    st.session_state["forecast_hour_1"] = FORECAST_HOUR_1
if "forecast_hour_2" not in st.session_state:
    st.session_state["forecast_hour_2"] = FORECAST_HOUR_2

# Use these throughout the app
forecast_hour_1 = st.session_state["forecast_hour_1"]
forecast_hour_2 = st.session_state["forecast_hour_2"]

# Use session_state to store last fetched city and weather
if "last_city" not in st.session_state:
    st.session_state["last_city"] = ""
if "outdoor_temp_fetched" not in st.session_state:
    st.session_state["outdoor_temp_fetched"] = None
if "outdoor_rh_fetched" not in st.session_state:
    st.session_state["outdoor_rh_fetched"] = None
if "forecast_6h" not in st.session_state:
    st.session_state["forecast_6h"] = None
if "forecast_12h" not in st.session_state:
    st.session_state["forecast_12h"] = None
if "debug_info" not in st.session_state:
    st.session_state["debug_info"] = ""


# Only fetch if city changed or GPS is used
if city:
    # If city is entered, override GPS and use city for weather
    if city != st.session_state["last_city"]:
        temp, humidity, forecast_6h, forecast_12h, debug_info = get_weather(
            city, OPENWEATHER_API_KEY
        )
        st.session_state["last_city"] = city
        st.session_state["debug_info"] = debug_info
        if temp is not None:
            st.session_state["outdoor_temp_fetched"] = temp
            st.session_state["outdoor_rh_fetched"] = humidity
            st.session_state["forecast_6h"] = forecast_6h
            st.session_state["forecast_12h"] = forecast_12h
        else:
            st.session_state["outdoor_temp_fetched"] = None
            st.session_state["outdoor_rh_fetched"] = None
            st.session_state["forecast_6h"] = None
            st.session_state["forecast_12h"] = None
elif use_gps:
    # Only use GPS if city is empty
    temp, humidity, forecast_6h, forecast_12h, debug_info = fetch_weather_by_gps(
        lat, lon, OPENWEATHER_API_KEY
    )
    st.session_state["last_city"] = f"GPS:{lat},{lon}"
    st.session_state["debug_info"] = debug_info
    if temp is not None:
        st.session_state["outdoor_temp_fetched"] = temp
        st.session_state["outdoor_rh_fetched"] = humidity
        st.session_state["forecast_6h"] = forecast_6h
        st.session_state["forecast_12h"] = forecast_12h
    else:
        st.session_state["outdoor_temp_fetched"] = None
        st.session_state["outdoor_rh_fetched"] = None
        st.session_state["forecast_6h"] = None
        st.session_state["forecast_12h"] = None

outdoor_temp_fetched = st.session_state["outdoor_temp_fetched"]
outdoor_rh_fetched = st.session_state["outdoor_rh_fetched"]
forecast_6h = st.session_state["forecast_6h"]
forecast_12h = st.session_state["forecast_12h"]
debug_info = st.session_state["debug_info"]

# Always define the input fields, dew point calculations, and plot before the weather fetch result check
col2, col1 = st.columns(2)
with col2:
    # If fetched values exist, use them as defaults
    if outdoor_temp_fetched is not None and outdoor_rh_fetched is not None:
        outdoor_temp = st.number_input(
            "Outdoor temperature (°C)",
            min_value=-30.0,
            max_value=40.0,
            value=float(outdoor_temp_fetched),
            step=0.5,
        )
        outdoor_rh = st.number_input(
            "Outdoor relative humidity (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(outdoor_rh_fetched),
            step=1.0,
        )
    else:
        outdoor_temp = st.number_input(
            "Outdoor temperature (°C)",
            min_value=-30.0,
            max_value=40.0,
            value=10.0,
            step=0.5,
        )
        outdoor_rh = st.number_input(
            "Outdoor relative humidity (%)",
            min_value=0.0,
            max_value=100.0,
            value=70.0,
            step=1.0,
        )
with col1:
    indoor_temp = st.number_input(
        "Indoor temperature (°C)", min_value=0.0, max_value=40.0, value=25.0, step=0.5
    )
    indoor_rh = st.number_input(
        "Indoor relative humidity (%)",
        min_value=0.0,
        max_value=100.0,
        value=60.0,
        step=1.0,
    )

# Calculate dew points
indoor_dp = calculate_dew_point(indoor_temp, indoor_rh)
outdoor_dp = calculate_dew_point(outdoor_temp, outdoor_rh)

# If points overlap, nudge them slightly for visibility
nudge = 0.15 if (indoor_temp == outdoor_temp and indoor_rh == outdoor_rh) else 0
indoor_x = indoor_temp + nudge
outdoor_x = outdoor_temp - nudge

# Plotly heatmap — blue (low DP) ➜ red (high DP)
blue_red_scale = [[0.0, "blue"], [1.0, "red"]]

fig = go.Figure(
    data=go.Heatmap(
        x=temperatures,
        y=humidities,
        z=dew_points,
        colorscale=blue_red_scale,
        colorbar=dict(title="Dew Point (°C)"),
        hovertemplate=(
            "Temperature: %{x:.1f}°C<br>"
            "Humidity: %{y:.0f}%<br>"
            "Dew Point: %{z:.2f}°C<extra></extra>"
        ),
        text=text_labels,
        texttemplate="%{text}",
        textfont={"size": 8, "color": "black"},
    )
)

fig.update_layout(
    title="Dew Point Temperature (°C)",
    xaxis_title="Temperature (°C)",
    yaxis_title="Relative Humidity (%)",
    template="plotly_white",
)

# Reduce the number of tick labels on both axes
x_tick_step = 1  # Show every temperature
y_tick_step = 1  # Show every humidity

fig.update_xaxes(
    tickvals=temperatures[::x_tick_step],
    ticktext=[f"{t:.0f}" for t in temperatures[::x_tick_step]],
    tickangle=0,
    title_font=dict(size=20),  # Increase axis label font size
    tickfont=dict(size=16),  # Increase tick label font size
)
fig.update_yaxes(
    tickvals=humidities[::y_tick_step],
    ticktext=[f"{h:.0f}" for h in humidities[::y_tick_step]],
    title_font=dict(size=20),  # Increase axis label font size
    tickfont=dict(size=16),  # Increase tick label font size
)

# Reduce the number of text labels inside the heatmap for readability
sparse_text_labels = np.empty_like(text_labels, dtype=object)
for i in range(len(humidities)):
    for j in range(len(temperatures)):
        if i % y_tick_step == 0 and j % x_tick_step == 0:
            sparse_text_labels[i, j] = text_labels[i, j]
        else:
            sparse_text_labels[i, j] = ""

# Update the heatmap trace to use sparse_text_labels
fig.data[0].text = sparse_text_labels

# Add large dots for indoor and outdoor points with offset text positions
fig.add_trace(
    go.Scatter(
        x=[indoor_x],
        y=[indoor_rh],
        mode="markers+text",
        marker=dict(size=18, color="green", line=dict(width=2, color="black")),
        name="Indoor",
        text=[f"Indoor\nDP: {indoor_dp:.2f}°C"],
        textposition="top center",
        textfont=dict(size=12, color="white", weight="bold"),
        hovertemplate=(
            f"<b>Indoor</b><br>Temp: %{{x:.1f}}°C<br>RH: %{{y:.0f}}%<br>"
            f"Dew Point: {indoor_dp:.2f}°C<extra></extra>"
        ),
    )
)
fig.add_trace(
    go.Scatter(
        x=[outdoor_x],
        y=[outdoor_rh],
        mode="markers+text",
        marker=dict(size=18, color="blue", line=dict(width=2, color="black")),
        name="Outdoor",
        text=[f"Outdoor\nDP: {outdoor_dp:.2f}°C"],
        textposition="top center",
        textfont=dict(size=12, color="white", weight="bold"),
        hovertemplate=(
            f"<b>Outdoor</b><br>Temp: %{{x:.1f}}°C<br>RH: %{{y:.0f}}%<br>"
            f"Dew Point: {outdoor_dp:.2f}°C<extra></extra>"
        ),
    )
)

fig.update_layout(
    legend=dict(
        orientation="h",
        x=0.5,
        y=-0.2,
        xanchor="center",
        yanchor="top",
        font=dict(size=14),
    )
)


def to_local_time(dt_str):
    # dt_str is in format 'YYYY-MM-DD HH:MM:SS' and UTC
    utc_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    local_tz = pytz.timezone("Europe/Tallinn")
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_dt.strftime("%H:%M")


# Only show plot and results if the weather fetch was successful
if outdoor_temp_fetched is not None and outdoor_rh_fetched is not None:
    # Ultra-compact single-row table for mobile
    label_6h = to_local_time(forecast_6h[2]) if forecast_6h else f"+{forecast_hour_1}h"
    label_12h = (
        to_local_time(forecast_12h[2]) if forecast_12h else f"+{forecast_hour_2}h"
    )
    all_table = [
        [
            (
                f"{outdoor_temp_fetched:.1f}°C, {outdoor_rh_fetched:.0f}%"
                if outdoor_temp_fetched is not None
                else ""
            ),
            (f"{forecast_6h[0]:.1f}°C, {forecast_6h[1]:.0f}%" if forecast_6h else ""),
            (
                f"{forecast_12h[0]:.1f}°C, {forecast_12h[1]:.0f}%"
                if forecast_12h
                else ""
            ),
            f"{indoor_dp:.1f}°C",
            f"{outdoor_dp:.1f}°C",
            "✅" if outdoor_dp <= indoor_dp - 2 else "❌",
        ],
    ]
    # Custom HTML table for mobile
    labels = [
        "Now",
        f"{label_6h}",
        f"{label_12h}",
        "In DP",
        "Out DP",
        "HRV?",
    ]
    row = all_table[0]
    table_header = "".join(f"<th>{label}</th>" for label in labels)
    table_row = "".join(f"<td>{cell}</td>" for cell in row)
    table_html = f"""
    <table style='width:100%; font-size:0.9em; text-align:center;'>
      <tr>
        {table_header}
      </tr>
      <tr>
        {table_row}
      </tr>
    </table>
    """
    st.markdown(table_html, unsafe_allow_html=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("City not found or API error.")
    if debug_info:
        st.code(debug_info, language="text")

# After the plot, title, and description, but before the detected location:
st.markdown("---")

# After the plot and results, add the title and description at the end
st.subheader("Dew Point Ventilation Advisor")
st.markdown(
    """
This app is a simple tool to help you decide whether to ventilate your home based on the indoor and outdoor conditions.\
It calculates the dew point for both indoor and outdoor and displays them in a heatmap.\
It also provides a suggestion for HRV homeowners, based on the difference between the indoor and outdoor dew points.
"""
)

# --- Beach water temperature integration (using new Estonian Environment Agency API) ---
# import requests  # REMOVE this duplicate import if already imported at the top


# Replace deg_to_compass with 8-direction version
def deg_to_compass(deg):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    try:
        deg = float(deg)
        ix = int((deg / 45) + 0.5) % 8
        return dirs[ix]
    except Exception:
        return str(deg)


# Only try to show if GPS is available
if "lat" in locals() and "lon" in locals() and lat is not None and lon is not None:
    stations = fetch_estonian_beach_temps()
    if stations:
        nearest = find_nearest_station(lat, lon, stations)
        if nearest:
            st.subheader("Nearest beach:")
            st.markdown(f"{nearest['name']}")
            st.markdown(f"**Water temperature:** {nearest['temp']:.1f}°C")
            # Highlight air temperature, wind speed, and wind direction if available
            air_temp = nearest.get("ta1ha")
            wind_speed = nearest.get("ws1hx")
            wind_dir = nearest.get("wd10ma")
            if air_temp:
                st.markdown(f"**Air temperature:** {air_temp} °C")
            if wind_speed:
                try:
                    wind_speed_float = float(str(wind_speed).replace(",", "."))
                    wind_speed_kmh = wind_speed_float * 3.6
                    st.markdown(
                        f"**Wind speed:** {wind_speed_float:.1f} m/s ({wind_speed_kmh:.1f} km/h)"
                    )
                except Exception:
                    st.markdown(f"**Wind speed:** {wind_speed} m/s")
            if wind_dir:
                try:
                    wind_dir_int = int(round(float(wind_dir)))
                except Exception:
                    wind_dir_int = wind_dir
                st.markdown(
                    f"**Wind direction:** {wind_dir_int}° ({deg_to_compass(wind_dir)})"
                )
                # Show measurement time/date if available
                measurement_time = nearest.get("Time")
                if measurement_time:
                    # Try to parse ISO format and display as 'DD.MM.YYYY HH:MM'
                    try:
                        dt = datetime.fromisoformat(
                            measurement_time.replace("Z", "+00:00")
                        )
                        st.markdown(
                            f"**Measurement time:** {dt.strftime('%d.%m.%Y %H:%M')}"
                        )
                    except Exception:
                        st.markdown(f"**Measurement time:** {measurement_time}")
                # Show station distance to user location
                user_coords = (lat, lon)
                station_coords = (nearest.get("lat"), nearest.get("lon"))
                from beach_weather import haversine

                dist_km = haversine(lat, lon, station_coords[0], station_coords[1])
                st.code(
                    f"Station distance to user location: {dist_km:.2f} km",
                    language="text",
                )

# --- Estonian Environment Agency Humidity Comparison ---
from beach_weather import fetch_estonian_humidity_map, find_nearest_humidity_station

if "lat" in locals() and "lon" in locals() and lat is not None and lon is not None:
    # Determine local timezone for user's coordinates
    tf = TimezoneFinder()
    user_tz_str = tf.timezone_at(lat=lat, lng=lon) or "Europe/Tallinn"
    user_tz = pytz.timezone(user_tz_str)
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc.astimezone(user_tz)
    found = False
    for hour_offset in range(0, 4):
        dt = now_local - timedelta(hours=hour_offset)
        date_str = dt.strftime("%Y-%m-%d")
        hour_str = dt.strftime("%H")
        stations = fetch_estonian_humidity_map(date_str, hour_str)
        stations = [s for s in stations if s.get("humidity") is not None]
        if stations:
            nearest = find_nearest_humidity_station(lat, lon, stations)
            if nearest and nearest.get("humidity") is not None:
                st.markdown("---")
                st.subheader("Estonian Environment Agency Humidity (nearest station)")
                st.markdown(f"**Station:** {nearest.get('Jaam','?')}")
                # Format timestamp for easier reading in local time
                dt_obj = user_tz.localize(
                    datetime.strptime(f"{date_str} {hour_str}", "%Y-%m-%d %H")
                )
                formatted_time = dt_obj.strftime("%H:00, %d.%m.%Y %Z")
                st.markdown(
                    f"**Relative humidity:** {nearest['humidity']:.0f}% (at {formatted_time})"
                )
                # Debug info: show user and station coordinates and distance
                user_coords = (lat, lon)
                station_coords = (nearest.get("lat"), nearest.get("lon"))
                from beach_weather import haversine

                dist_km = haversine(lat, lon, station_coords[0], station_coords[1])
                st.code(
                    # f"User location: {user_coords}\nStation location: {station_coords}\nDistance: {dist_km:.2f} km",
                    f"Station distance to user location: {dist_km:.2f} km",
                    language="text",
                )
                found = True
                break
    if not found:
        st.info("No recent Estonian humidity data available for your location.")
    # Also show OpenWeatherMap humidity for comparison
    if outdoor_rh_fetched is not None:
        st.markdown(
            f"**OpenWeatherMap humidity (your GPS):** {outdoor_rh_fetched:.0f}% (current)"
        )
