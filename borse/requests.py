import decimal
from borse.api import *
from borse.request_base import *

class RegisterRequest(RequestBase):

    def unpack(self, params):
        if not self._check_spec(params, [str, 'email', str]):
            return False

        self.username, self.email, self.password = params
        return True

    async def process(self, connection, db):
        return await create_account(db, self.id, 
                                    self.username, self.email, self.password)

class LoginRequest(RequestBase):

    def unpack(self, params):
        if not self._check_spec(params, [str, str, 'public_key']):
            return False

        self.username, self.password, session_key = params
        self.session_key = bytes.fromhex(session_key)
        return True

    async def process(self, connection, db):
        return await login(connection, db, self.id,
                           self.username, self.password, self.session_key)

class FetchOrderbook(RequestBase):

    def unpack(self, params):
        if not self._check_spec(params, ['currency_code', 'currency_code']):
            return False
        self.base, self.quote = params
        return True

    async def process(self, connection, db):
        return await fetch_orderbook(db, self.id, self.base, self.quote)

class FetchTrades(RequestBase):

    def unpack(self, params):
        if not self._check_spec(params, ['currency_code', 'currency_code']):
            return False
        self.base, self.quote = params
        return True

    async def process(self, connection, db):
        return await fetch_trades(db, self.id, self.base, self.quote)

class TickerInfo(RequestBase):

    def unpack(self, params):
        if not self._check_spec(params, ['currency_code', 'currency_code']):
            return False
        self.base, self.quote = params
        return True

    async def process(self, connection, db):
        return await query_ticker_info(db, self.id, self.base, self.quote)

#########################################
#       AUTHENTICATED REQUESTS          #
#########################################

class HelloRequest(RequestBase):

    def unpack(self, params):
        if not self._check_spec(params, [str]):
            return False
        self.message = params[0]
        return True

    async def process(self, connection, db):
        print('hello')
        return make_response(self.id, None)

class PlaceOrderRequest(RequestBase):

    def unpack(self, params):
        if not self._check_spec(params, [
            'currency_code', 'currency_code', 'order_value', 'order_value',
            'order_type']):
            return False
        self.base, self.quote, self.price, self.amount, self.type = params
        self.price = decimal.Decimal(self.price)
        self.amount = decimal.Decimal(self.amount)
        return True

    async def process(self, connection, db):
        assert connection.user_id is not None
        return await place_order(connection, db, self.id, connection.user_id,
            self.base, self.quote, self.price, self.amount, self.type)

class FetchAccounts(RequestBase):

    def unpack(self, params):
        return not params

    async def process(self, connection, db):
        assert connection.user_id is not None
        return await fetch_accounts(db, self.id, connection.user_id)

class GetBitcoinDepositAddress(RequestBase):

    def unpack(self, params):
        return not params

    async def process(self, connection, db):
        assert connection.user_id is not None
        return await get_bitcoin_deposit_address(
            db, self.id, connection.user_id)

class WithdrawBitcoin(RequestBase):

    def unpack(self, params):
        if not self._check_spec(params, ['bitcoin_address', 'amount']):
            return False
        self.address, self.amount = params
        return True

    async def process(self, connection, db):
        return await make_withdraw_bitcoin_request(
            db, self.id, connection.user_id, self.address, self.amount)

request_types = {
    'register': RegisterRequest,
    'login': LoginRequest,
    'fetch_orderbook': FetchOrderbook,
    'fetch_trades': FetchTrades,
    'ticker_info': TickerInfo
}

authenticated_request_types = {
    'say_hello': HelloRequest,
    'place_order': PlaceOrderRequest,
    'fetch_accounts': FetchAccounts,
    'get_bitcoin_deposit_address': GetBitcoinDepositAddress,
    'withdraw_bitcoin': WithdrawBitcoin
}

