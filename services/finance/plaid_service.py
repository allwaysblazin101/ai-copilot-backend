from plaid.api import plaid_api
from plaid.configuration import Configuration
from plaid.api_client import ApiClient

from backend.config.settings import (
    PLAID_CLIENT_ID,
    PLAID_SECRET,
    PLAID_ENV
)

configuration = Configuration(
    host=f"https://{PLAID_ENV}.plaid.com"
)

client = plaid_api.PlaidApi(ApiClient(configuration))

def get_balance(access_token):
    request = {
        "access_token": access_token
    }
    return client.accounts_balance_get(request)