from backend.services.finance.ibkr_service import IBKRService


def test_ibkr_account_summary_smoke():
    svc = IBKRService(host="127.0.0.1", port=4002, client_id=101)
    result = svc.get_account_summary()

    assert isinstance(result, dict)
    assert "success" in result
