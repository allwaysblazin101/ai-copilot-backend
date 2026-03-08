import httpx
from backend.tools.registry import register_tool # Updated path based on your earlier logs

class WeatherTool:
    async def get_weather(self, location="Toronto"):
        coords = await self._geocode(location)
        if not coords:
            return {"error": f"Location '{location}' not found"}

        lat, lon = coords["lat"], coords["lon"]
        # FIXED: Added /v1/forecast and ?latitude=
        url = f"https://api.open-meteo.com{lat}&longitude={lon}&current_weather=true"

        async with httpx.AsyncClient() as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()["current_weather"]

        return {
            "location": location,
            "temperature_c": data["temperature"],
            "wind_kph": data["windspeed"],
            "time": data["time"]
        }

    async def _geocode(self, location):
        # FIXED: Added /v1/search
        url = "https://geocoding-api.open-meteo.com/v1/search"
        async with httpx.AsyncClient() as client:
            r = await client.get(url, params={"name": location, "count": 1})
            r.raise_for_status()
            data = r.json()
            if "results" not in data or not data["results"]: 
                return None
            res = data["results"][0]
            return {"lat": res["latitude"], "lon": res["longitude"]}

# --- REGISTRATION ---
weather_instance = WeatherTool()

@register_tool("weather", "Get current weather for a location")
async def get_weather_tool(location="Toronto"):
    # Ensure we pass the location string, not the full payload dict if coming from MasterBrain
    loc = location.get("location", "Toronto") if isinstance(location, dict) else location
    return await weather_instance.get_weather(loc)
