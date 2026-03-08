import os
import requests

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

def get_stock_price(symbol):

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"

    params = {
        "apiKey": POLYGON_API_KEY
    }

    r = requests.get(url, params=params)

    return r.json()