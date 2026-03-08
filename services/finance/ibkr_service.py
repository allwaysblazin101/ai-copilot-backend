from ib_insync import IB

ib = IB()

def connect_ibkr(host="127.0.0.1", port=7497, client_id=1):
    return ib.connect(host, port, clientId=client_id)

def get_portfolio():
    if not ib.isConnected():
        connect_ibkr()

    return ib.portfolio()