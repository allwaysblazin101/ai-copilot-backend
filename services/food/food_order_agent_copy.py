import requests
from backend.config.settings import settings

class FoodOrderAgent:
    def __init__(self):
        # Use your central settings to get the key
        self.api_key = os.getenv("ORDEROUT_API_KEY")
        self.base_url = "https://api.orderout.co/api"

    def find_restaurants(self, query="pizza"):
        """Search for restaurants using the OrderOut POS API."""
        if not self.api_key:
            return {"error": "Missing ORDEROUT_API_KEY"}

        # Correct OrderOut endpoint for listing restaurants
        url = f"{self.base_url}/pos/account/restaurants"
        
        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self.api_key}" # Standard Bearer token
        }

        try:
            # OrderOut typically uses standard GET for lists
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"OrderOut Search Failed: {str(e)}"}

    async def get_test_quote(self, order_details: str):
        """
        Mock a quote for your test. 
        In production, this would call /delivery/quotes
        """
        # Simulated price for your cheese and grilled chicken pizza test
        return {
            "item": order_details,
            "total_price": 22.50,
            "currency": "usd"
        }
