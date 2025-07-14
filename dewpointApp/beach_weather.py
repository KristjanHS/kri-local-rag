import requests
import xml.etree.ElementTree as ET
from math import radians, cos, sin, asin, sqrt


def haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


def fetch_estonian_beach_temps():
    url = "https://publicapi.envir.ee/v1/combinedWeatherData/coastalSeaStationsWeatherToday"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        stations = []
        root = ET.fromstring(response.content)
        ns = {"ns0": "http://ws.wso2.org/dataservice/coastalSeaStationsWeatherToday"}

        def dms_to_decimal(deg, min, sec):
            return float(deg) + float(min) / 60 + float(sec) / 3600

        for entry in root.findall(".//ns0:entry", ns):
            # Collect all fields in the entry
            station_data = {}
            for child in entry:
                tag = child.tag.split("}", 1)[-1]  # Remove namespace
                station_data[tag] = child.text
            # Add calculated decimal lat/lon if possible
            try:
                lat = dms_to_decimal(
                    station_data.get("LaiusKraad"),
                    station_data.get("LaiusMinut"),
                    station_data.get("LaiusSekund"),
                )
                lon = dms_to_decimal(
                    station_data.get("PikkusKraad"),
                    station_data.get("PikkusMinut"),
                    station_data.get("PikkusSekund"),
                )
                station_data["lat"] = lat
                station_data["lon"] = lon
            except Exception:
                pass
            # Use "ametliknimi" or "Jaam" as name
            station_data["name"] = station_data.get("ametliknimi") or station_data.get(
                "Jaam"
            )
            # Add float water temp if possible
            if station_data.get("wt1ha"):
                try:
                    station_data["temp"] = float(
                        station_data["wt1ha"].replace(",", ".")
                    )
                except Exception:
                    pass
            stations.append(station_data)
        return stations
    except Exception:
        return []


def find_nearest_station(user_lat, user_lon, stations):
    min_dist = float("inf")
    nearest = None
    for station in stations:
        dist = haversine(user_lat, user_lon, station["lat"], station["lon"])
        if dist < min_dist:
            min_dist = dist
            nearest = station
    return nearest
