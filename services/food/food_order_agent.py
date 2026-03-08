import requests
import os
from backend.config.settings import settings

class FoodOrderAgent:
    def __init__(self):
        # Using the sandbox key you provided
        self.api_key = "3dxCNw4SZkAoRu2wcVmThxxpwzYwSwJq" 
        self.base_url = "https://api.orderout.co/api"

    def find_restaurants(self, query="pizza"):
        """Search for restaurants in the OrderOut Sandbox."""
        url = f"{self.base_url}/pos/account/restaurants"
        headers = {
            "accept": "application/json",
            "api-key": self.api_key 
        }
        try:
            response = requests.get(url, headers=headers)
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    async def get_test_quote(self, order_details: str):
        """Mock a price for the sandbox test."""
        return {
            "item": order_details,
            "total_price": 22.50,
            "currency": "usd"
        }

    async def process_order(self, query: str):
        # 1. Search for actual restaurants in the Sandbox
        search_results = self.find_restaurants(query)
        
        # 2. Pick the first restaurant or use a fallback
        if isinstance(search_results, list) and len(search_results) > 0:
            restaurant = search_results[0]
            name = restaurant.get("name", "Local Pizza Shop")
            eta = "35-45 minutes" 
        else:
            name = "Pizza Palace (Sandbox)"
            eta = "30 minutes"

        # 3. Get the quote/price
        quote = await self.get_test_quote(query)
        
        return {
            "restaurant_name": name,
            "eta": eta,
            "total_price": quote["total_price"]
        }
