import pytest

from backend.services.replies.reply_service import ReplyService


@pytest.mark.asyncio
async def test_last_order_roundtrip():
    svc = ReplyService()
    owner = "14160000002"

    sample = {
        "success": True,
        "submitted_order": {
            "orderId": 99,
            "symbol": "AAPL",
            "action": "BUY",
            "quantity": 1,
            "orderType": "MKT",
        },
        "order_status": [
            {
                "orderId": 99,
                "status": "Submitted",
                "filled": 0,
                "remaining": 1,
                "avgFillPrice": 0.0,
                "lastFillPrice": 0.0,
                "clientId": 123,
            }
        ],
        "errors": [],
    }

    ok = await svc.save_last_order(owner, sample)
    assert ok is True

    loaded = await svc.get_last_order(owner)
    assert loaded is not None
    assert loaded["order_result"]["submitted_order"]["symbol"] == "AAPL"