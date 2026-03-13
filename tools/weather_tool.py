import httpx
from backend.tools.registry import register_tool


class WeatherTool:
    async def get_weather(self, location: str = "Toronto"):
        coords = await self._geocode(location)
        if not coords:
            return {"error": f"Location '{location}' not found"}

        lat, lon = coords["lat"], coords["lon"]
        url = "https://api.open-meteo.com/v1/forecast"

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": "true",
                },
            )
            r.raise_for_status()
            data = r.json().get("current_weather")

        if not data:
            return {"error": "Weather data unavailable"}

        return {
            "location": location,
            "temperature_c": data.get("temperature"),
            "wind_kph": data.get("windspeed"),
            "time": data.get("time"),
        }

    async def _geocode(self, location: str):
        url = "https://geocoding-api.open-meteo.com/v1/search"

        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                url,
                params={
                    "name": location,
                    "count": 1,
                },
            )
            r.raise_for_status()
            data = r.json()

        if "results" not in data or not data["results"]:
            return None

        res = data["results"][0]
        return {
            "lat": res["latitude"],
            "lon": res["longitude"],
        }


weather_instance = WeatherTool()


@register_tool("weather", "Get current weather for a location")
async def get_weather_tool(location="Toronto"):
    loc = location.get("location", "Toronto") if isinstance(location, dict) else location
    return await weather_instance.get_weather(loc)