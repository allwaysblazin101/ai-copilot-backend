import stripe
from backend.config.settings import settings

class StripeService:
    def __init__(self):
        # This pulls your sk_test_... from the .env
        self.api_key = settings.stripe_secret_key.get_secret_value()
        stripe.api_key = self.api_key

    def create_checkout_session(self, item_name: str, amount: float):
        """Generates a test payment link."""
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': item_name},
                        'unit_amount': int(amount * 100),  # Stripe uses cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url="https://example.com",
                cancel_url="https://example.com",
            )
            return session.url
        except Exception as e:
            return f"Stripe Error: {str(e)}"
