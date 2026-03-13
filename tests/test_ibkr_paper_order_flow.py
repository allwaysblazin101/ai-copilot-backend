import pytest

from backend.services.replies.reply_service import ReplyService


@pytest.mark.asyncio
async def test_pending_trade_roundtrip():
    svc = ReplyService()
    owner = "14160000001"

    ok = await svc.save_pending_trade(
        owner_number=owner,
        symbol="AAPL",
        action="BUY",
        quantity=1,
    )
    assert ok is True

    pending = await svc.get_pending_trade(owner)
    assert pending is not None
    assert pending["symbol"] == "AAPL"
    assert pending["action"] == "BUY"
    assert pending["quantity"] == 1

    cleared = await svc.clear_pending_trade(owner)
    assert cleared is True

    pending_after = await svc.get_pending_trade(owner)
    assert pending_after is None