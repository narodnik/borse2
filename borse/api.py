import asyncpg
import json
import re
import borse.bitcoin_api
import borse.utility
from passlib.apps import custom_app_context as password_context
from passlib.hash import sha256_crypt

class ResponseError:

    UNIMPLEMENTED = 'unimplemented'
    INVALID_USERNAME = 'invalid username'
    DUPLICATE_USERNAME = 'duplicate username'
    NONEXISTENT_USERNAME = 'nonexistent username'
    WRONG_PASSWORD = 'wrong password'
    NONUNIQUE_SESSION_KEY = 'nonunique session_key'
    INSUFFICIENT_BALANCE = 'insufficient balance'

def make_response(request_id, result):
    return {
        'id': request_id,
        'error': None,
        'result': result
    }

def make_error_response(request_id, error):
    return {
        'id': request_id,
        'error': error,
        'result': None
    }

async def create_account(db, request_id, username, email, password):
    if not re.match('^[a-zA-Z0-9_.]+$', username):
        return make_error_response(request_id, ResponseError.INVALID_USERNAME)

    password_hash = sha256_crypt.hash(password)

    user_id = await db.fetchval('select create_user($1, $2, $3)',
                                username, email, password_hash)

    if user_id is None:
        return make_error_response(request_id, ResponseError.DUPLICATE_USERNAME)

    print('Registered user "%s" (%s)' % (username, user_id))

    return make_response(request_id, None)

async def log_password_login_attempt(db, success, auth_id, session_id):
    await db.execute('''
        insert into password_login_attempts (
            was_successful, auth_id, session_id
        ) values ($1, $2, $3)
    ''', success, auth_id, session_id)

async def login(connection, db, request_id, username, password, session_key):
    row = await db.fetchrow('''
        select users.user_id, auth_id, password_hash
        from users
        join password_authentication
        on password_authentication.user_id=users.user_id
        where username = $1
    ''', username)
    if row is None:
        await log_password_login_attempt(db, False, None, None)
        return make_error_response(request_id,
                                   ResponseError.NONEXISTENT_USERNAME)

    user_id, auth_id, password_hash = row

    if not password_context.verify(password, password_hash):
        await log_password_login_attempt(db, False, auth_id, None)
        return make_error_response(request_id, ResponseError.WRONG_PASSWORD)

    try:
        session_id = await db.fetchval('''
            select login($1, $2)
        ''', auth_id, session_key)
    except asyncpg.exceptions.UniqueViolationError:
        return make_error_response(request_id,
                                   ResponseError.NONUNIQUE_SESSION_KEY)

    connection.accept_authentication(user_id, session_key)

    return make_response(request_id, None)

async def place_order(connection, db, request_id, user_id, base, quote,
                      price, amount, order_type):
    assert borse.utility.decimal_has_correct_precision(price, 4)
    assert borse.utility.decimal_has_correct_precision(amount, 4)

    assert order_type in ('Buy', 'Sell')

    if order_type == 'Buy':
        deduct_currency = quote
        deduct_amount = amount * price
    else:
        deduct_currency = base
        deduct_amount = amount

    assert borse.utility.decimal_has_correct_precision(amount, 8)

    try:
        row = await db.fetchrow('''
            select place_order($1, $2, $3, $4, $5, $6)
        ''', user_id, base, quote, price, amount, order_type)
    except asyncpg.exceptions.CheckViolationError:
        return make_error_response(request_id,
                                   ResponseError.INSUFFICIENT_BALANCE)

    assert (deduct_currency, deduct_amount) == row[0], row[1]
    print('Placed order for user(%s) [%s %s %s @ %s %s], deducted %s %s' % (
        user_id, order_type, amount, base, price, quote,
        deduct_amount, deduct_currency))

    await connection.broadcast('ok', 'order', {
        'amount': f'{amount:.4f}',
        'price': f'{price:.4f}',
        'order_type': order_type,
        'base': base,
        'quote': quote
    })

    return make_response(request_id, None)

async def fetch_orderbook(db, request_id, base, quote):
    orderbook_json = await db.fetchval('''
        select array_to_json(array_agg(row_to_json(result)))
        from (
            select
                price::varchar,
                remaining_amount(order_id)::varchar as amount,
                order_type,
                extract(epoch from created_at) as timestamp
            from orders
            where
                base_currency = $1 and quote_currency = $2 and
                status = 'Open'
        ) as result
    ''', base, quote)
    assert orderbook_json is not None
    return make_response(request_id, json.loads(orderbook_json))

async def fetch_trades(db, request_id, base, quote):
    trades_json = await db.fetchval('''
        select array_to_json(array_agg(row_to_json(result)))
        from (
            select
                trade_price::varchar as price,
                trade_amount::varchar as amount,
                extract(epoch from trades.created_at) as timestamp
            from trades
            join orders on buy_id = order_id
            where
                base_currency = $1 and quote_currency = $2 and
                trades.created_at > now() - interval '24 hours'
        ) as result
    ''', base, quote)
    assert trades_json is not None
    return make_response(request_id, json.loads(trades_json))

async def fetch_accounts(db, request_id, user_id):
    accounts_json = await db.fetchval('''
        select array_to_json(array_agg(row_to_json(result)))
        from (
            select currency_code, balance::varchar
            from accounts
            where user_id = $1
        ) as result
    ''', user_id)
    assert accounts_json is not None
    return make_response(request_id, json.loads(accounts_json))

async def query_ticker_info(db, request_id, base, quote):
    ticker_json = await db.fetchval(
        'select query_ticker_info($1, $2)',
        base, quote)
    assert ticker_json is not None
    ticker_data = json.loads(ticker_json)
    assert len(ticker_data) == 1
    ticker_data = ticker_data[0]
    return make_response(request_id, ticker_data)

async def get_bitcoin_deposit_address(db, request_id, user_id):
    current_chain_index = await db.fetchval(
        'select current_bitcoin_chain_index($1)', user_id)

    address = borse.bitcoin_api.get_address(user_id, current_chain_index)

    return make_response(request_id, address)

async def make_withdraw_bitcoin_request(
    db, request_id, user_id, address, amount):
    try:
        await db.execute(
            'select make_withdraw_bitcoin_request($1, $2, $3, $4)',
            user_id, address, amount, 0)
    except asyncpg.exceptions.CheckViolationError:
        return make_error_response(request_id,
                                   ResponseError.INSUFFICIENT_BALANCE)

    return make_response(request_id, None)

