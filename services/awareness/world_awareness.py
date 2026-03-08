import requests

class WorldAwareness:

    def get_weather(self, city="Toronto"):

        try:
            res = requests.get(
                f"https://wttr.in/{city}?format=j1",
                timeout=5
            )

            data = res.json()
            return data["current_condition"][0]

        except:
            return None
