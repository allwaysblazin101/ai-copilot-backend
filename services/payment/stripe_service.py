import stripe
from backend.config.settings import settings

stripe.api_key = settings.stripe_secret_key.get_secret_value()

class StripeService:
    def charge_saved_card(self, customer_id: str, amount: float, description: str):
        """AI triggers this after you say 'Correct'"""
        try:
            # In a real app, you'd retrieve the customer's default payment method
            payment_intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),
                currency="usd",
                customer=customer_id,
                payment_method="pm_card_visa", # In sandbox, this represents a saved Visa
                off_session=True, # Tells Stripe you aren't actively on a website
                confirm=True,
                description=description
            )
            return {"status": "success", "id": payment_intent.id}
        except Exception as e:
            return {"status": "error", "message": str(e)}
