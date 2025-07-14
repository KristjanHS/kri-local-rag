import requests
import numpy as np
from datetime import datetime, UTC, timezone

a_const: float = 17.625
b_const: float = 243.04


def get_weather(city, api_key):
    debug_info = ""
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={api_key}"
    resp = requests.get(url)
    debug_info += (
        f"URL tried: {url}\nStatus code: {resp.status_code}\nResponse: {resp.text}\n"
    )
    if resp.status_code == 200:
        data = resp.json()
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        lat = data["coord"]["lat"]
        lon = data["coord"]["lon"]
        forecast_url = (
            f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}"
            f"&units=metric&appid={api_key}"
        )
        forecast_resp = requests.get(forecast_url)
        debug_info += (
            f"Forecast URL tried: {forecast_url}\nStatus code: {forecast_resp.status_code}\n"
            f"Response: {forecast_resp.text[:300]}...\n"
        )
        forecast_6h = forecast_12h = None
        if forecast_resp.status_code == 200:
            forecast_data = forecast_resp.json()
            from datetime import timedelta

            now = datetime.now(UTC)
            target_6h = now + timedelta(hours=6)
            target_12h = now + timedelta(hours=12)
            closest_6h = min(
                forecast_data["list"],
                key=lambda x: abs(
                    datetime.fromtimestamp(x["dt"], tz=timezone.utc) - target_6h
                ),
            )
            closest_12h = min(
                forecast_data["list"],
                key=lambda x: abs(
                    datetime.fromtimestamp(x["dt"], tz=timezone.utc) - target_12h
                ),
            )
            forecast_6h = (
                closest_6h["main"]["temp"],
                closest_6h["main"]["humidity"],
                closest_6h["dt_txt"],
            )
            forecast_12h = (
                closest_12h["main"]["temp"],
                closest_12h["main"]["humidity"],
                closest_12h["dt_txt"],
            )
        return temp, humidity, forecast_6h, forecast_12h, debug_info
    if "," in city:
        city_parts = city.split(",")
        if len(city_parts) == 2:
            city_country = (
                f"{city_parts[0].strip()},{city_parts[1].strip()[:2].upper()}"
            )
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city_country}&units=metric&appid={api_key}"
            resp = requests.get(url)
            debug_info += f"URL tried: {url}\nStatus code: {resp.status_code}\nResponse: {resp.text}\n"
            if resp.status_code == 200:
                data = resp.json()
                temp = data["main"]["temp"]
                humidity = data["main"]["humidity"]
                lat = data["coord"]["lat"]
                lon = data["coord"]["lon"]
                forecast_url = (
                    f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}"
                    f"&units=metric&appid={api_key}"
                )
                forecast_resp = requests.get(forecast_url)
                debug_info += (
                    f"Forecast URL tried: {forecast_url}\nStatus code: {forecast_resp.status_code}\n"
                    f"Response: {forecast_resp.text[:300]}...\n"
                )
                forecast_6h = forecast_12h = None
                if forecast_resp.status_code == 200:
                    forecast_data = forecast_resp.json()
                    from datetime import timedelta

                    now = datetime.now(UTC)
                    target_6h = now + timedelta(hours=6)
                    target_12h = now + timedelta(hours=12)
                    closest_6h = min(
                        forecast_data["list"],
                        key=lambda x: abs(
                            datetime.fromtimestamp(x["dt"], tz=timezone.utc) - target_6h
                        ),
                    )
                    closest_12h = min(
                        forecast_data["list"],
                        key=lambda x: abs(
                            datetime.fromtimestamp(x["dt"], tz=timezone.utc)
                            - target_12h
                        ),
                    )
                    forecast_6h = (
                        closest_6h["main"]["temp"],
                        closest_6h["main"]["humidity"],
                        closest_6h["dt_txt"],
                    )
                    forecast_12h = (
                        closest_12h["main"]["temp"],
                        closest_12h["main"]["humidity"],
                        closest_12h["dt_txt"],
                    )
                return temp, humidity, forecast_6h, forecast_12h, debug_info
    return None, None, None, None, debug_info


def calculate_dew_point(temp_c: float, rh: float) -> float:
    alpha = np.log(rh / 100.0) + (a_const * temp_c) / (b_const + temp_c)
    return (b_const * alpha) / (a_const - alpha)


def fetch_weather_by_gps(lat, lon, api_key):
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={api_key}"
    resp = requests.get(url)
    debug_info = (
        f"URL tried: {url}\nStatus code: {resp.status_code}\nResponse: {resp.text}\n"
    )
    if resp.status_code == 200:
        data = resp.json()
        temp = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        forecast_url = (
            f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}"
            f"&units=metric&appid={api_key}"
        )
        forecast_resp = requests.get(forecast_url)
        debug_info += (
            f"Forecast URL tried: {forecast_url}\nStatus code: {forecast_resp.status_code}\n"
            f"Response: {forecast_resp.text[:300]}...\n"
        )
        forecast_6h = forecast_12h = None
        if forecast_resp.status_code == 200:
            forecast_data = forecast_resp.json()
            from datetime import timedelta

            now = datetime.now(UTC)
            target_6h = now + timedelta(hours=6)
            target_12h = now + timedelta(hours=12)
            closest_6h = min(
                forecast_data["list"],
                key=lambda x: abs(
                    datetime.fromtimestamp(x["dt"], tz=timezone.utc) - target_6h
                ),
            )
            closest_12h = min(
                forecast_data["list"],
                key=lambda x: abs(
                    datetime.fromtimestamp(x["dt"], tz=timezone.utc) - target_12h
                ),
            )
            forecast_6h = (
                closest_6h["main"]["temp"],
                closest_6h["main"]["humidity"],
                closest_6h["dt_txt"],
            )
            forecast_12h = (
                closest_12h["main"]["temp"],
                closest_12h["main"]["humidity"],
                closest_12h["dt_txt"],
            )
        return temp, humidity, forecast_6h, forecast_12h, debug_info
    return None, None, None, None, debug_info


def reverse_geocode(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json"
        resp = requests.get(url, headers={"User-Agent": "dewpoint-app/1.0"})
        if resp.status_code == 200:
            data = resp.json()
            return data.get("display_name")
    except Exception:
        pass
    return None


def get_js_geolocation():
    from streamlit_js_eval import streamlit_js_eval

    js_code = """
    new Promise((resolve, reject) => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude
                }),
                (err) => resolve({latitude: null, longitude: null, error: err.message})
            );
        } else {
            resolve({latitude: null, longitude: null, error: 'Geolocation not supported'});
        }
    })
    """
    return streamlit_js_eval(js_expressions=js_code, key="js_geo")


# Grid definitions for dew point heatmap
# (move these if needed for plotting)
temperatures = np.arange(13.0, 28.5, 2.0)
humidities = np.arange(50.0, 100.0, 8)
dew_points = np.empty((len(humidities), len(temperatures)))
for i, rh in enumerate(humidities):
    for j, t in enumerate(temperatures):
        dew_points[i, j] = calculate_dew_point(float(t), float(rh))
text_labels = np.empty_like(dew_points, dtype=object)
for i in range(len(humidities)):
    for j in range(len(temperatures)):
        text_labels[i, j] = f"{dew_points[i, j]:.0f}"
