# backend/services/finance/ibkr_service.py
import random
import threading
import time
from typing import Any, Dict, List, Optional

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

from backend.utils.logger import logger


class IBKRApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.account_summary_data: List[Dict[str, Any]] = []
        self.positions_data: List[Dict[str, Any]] = []
        self.open_orders_data: List[Dict[str, Any]] = []
        self.order_status_data: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.next_order_id: Optional[int] = None
        self.done = {
            "account_summary": False,
            "positions": False,
            "open_orders": False,
            "order_placed": False,
        }

    def nextValidId(self, orderId: int):
        self.next_order_id = orderId

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        self.errors.append(
            {
                "reqId": reqId,
                "code": errorCode,
                "message": errorString,
            }
        )

    def accountSummary(self, reqId, account, tag, value, currency):
        self.account_summary_data.append(
            {
                "account": account,
                "tag": tag,
                "value": value,
                "currency": currency,
            }
        )

    def accountSummaryEnd(self, reqId: int):
        self.done["account_summary"] = True

    def position(self, account, contract, position, avgCost):
        self.positions_data.append(
            {
                "account": account,
                "symbol": contract.symbol,
                "secType": contract.secType,
                "exchange": contract.exchange,
                "currency": contract.currency,
                "position": position,
                "avgCost": avgCost,
            }
        )

    def positionEnd(self):
        self.done["positions"] = True

    def openOrder(self, orderId, contract, order, orderState):
        self.open_orders_data.append(
            {
                "orderId": orderId,
                "symbol": contract.symbol,
                "secType": contract.secType,
                "action": order.action,
                "orderType": order.orderType,
                "totalQuantity": order.totalQuantity,
                "status": getattr(orderState, "status", ""),
            }
        )

    def openOrderEnd(self):
        self.done["open_orders"] = True

    def orderStatus(
        self,
        orderId,
        status,
        filled,
        remaining,
        avgFillPrice,
        permId,
        parentId,
        lastFillPrice,
        clientId,
        whyHeld,
        mktCapPrice,
    ):
        self.order_status_data.append(
            {
                "orderId": orderId,
                "status": status,
                "filled": filled,
                "remaining": remaining,
                "avgFillPrice": avgFillPrice,
                "lastFillPrice": lastFillPrice,
                "clientId": clientId,
            }
        )
        self.done["order_placed"] = True


class IBKRService:
    def __init__(self, host: str = "127.0.0.1", port: int = 4002, client_id: int | None = None):
        self.host = host
        self.port = port
        self.client_id = client_id

    def _make_client_id(self) -> int:
        return self.client_id if self.client_id is not None else random.randint(200, 9999)

    def _connect_app(self) -> tuple[IBKRApp, threading.Thread]:
        app = IBKRApp()
        client_id = self._make_client_id()
        logger.info(f"Connecting to IBKR on {self.host}:{self.port} with client_id={client_id}")
        app.connect(self.host, self.port, clientId=client_id)

        thread = threading.Thread(target=app.run, daemon=True)
        thread.start()

        timeout = time.time() + 8
        while app.next_order_id is None and time.time() < timeout:
            time.sleep(0.2)

        return app, thread

    def _disconnect_app(self, app: IBKRApp):
        try:
            if app.isConnected():
                app.disconnect()
        except Exception as e:
            logger.warning(f"IBKR disconnect warning: {e}")

    def get_account_summary(self) -> Dict[str, Any]:
        app, _ = self._connect_app()
        try:
            app.reqAccountSummary(9001, "All", "NetLiquidation,TotalCashValue,BuyingPower")
            timeout = time.time() + 10

            while not app.done["account_summary"] and time.time() < timeout:
                time.sleep(0.2)

            return {
                "success": True,
                "account_summary": app.account_summary_data,
                "errors": app.errors,
            }
        except Exception as e:
            logger.error(f"IBKR account summary failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            self._disconnect_app(app)

    def get_positions(self) -> Dict[str, Any]:
        app, _ = self._connect_app()
        try:
            app.reqPositions()
            timeout = time.time() + 10

            while not app.done["positions"] and time.time() < timeout:
                time.sleep(0.2)

            return {
                "success": True,
                "positions": app.positions_data,
                "errors": app.errors,
            }
        except Exception as e:
            logger.error(f"IBKR positions failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            self._disconnect_app(app)

    def get_open_orders(self) -> Dict[str, Any]:
        app, _ = self._connect_app()
        try:
            app.reqOpenOrders()
            timeout = time.time() + 10

            while not app.done["open_orders"] and time.time() < timeout:
                time.sleep(0.2)

            return {
                "success": True,
                "open_orders": app.open_orders_data,
                "errors": app.errors,
            }
        except Exception as e:
            logger.error(f"IBKR open orders failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            self._disconnect_app(app)

    def place_stock_market_order(self, symbol: str, action: str, quantity: int) -> Dict[str, Any]:
        app, _ = self._connect_app()
        try:
            if action not in {"BUY", "SELL"}:
                return {"success": False, "error": f"Unsupported action: {action}"}

            if quantity <= 0:
                return {"success": False, "error": "Quantity must be greater than zero"}

            if app.next_order_id is None:
                return {"success": False, "error": "IBKR did not return a valid order id"}

            contract = Contract()
            contract.symbol = symbol.upper()
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"

            order = Order()
            order.action = action
            order.orderType = "MKT"
            order.totalQuantity = quantity

            order_id = app.next_order_id
            logger.info(f"Placing paper market order order_id={order_id} {action} {quantity} {symbol.upper()}")

            app.placeOrder(order_id, contract, order)

            timeout = time.time() + 10
            while not app.done["order_placed"] and time.time() < timeout:
                time.sleep(0.2)

            return {
                "success": True,
                "submitted_order": {
                    "orderId": order_id,
                    "symbol": symbol.upper(),
                    "action": action,
                    "quantity": quantity,
                    "orderType": "MKT",
                },
                "order_status": app.order_status_data,
                "errors": app.errors,
            }
        except Exception as e:
            logger.error(f"IBKR place order failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            self._disconnect_app(app)