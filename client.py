import aioconsole
import asyncio
import ed25519
import json
import random
import websockets
from decimal import Decimal as D
from tabulate import tabulate
from termcolor import colored

id_command_map = {}

async def send(websocket, session, command, params):
    ident = random.randint(0, 2**32)
    message = json.dumps({
        'command': command,
        'id': ident,
        'params': params
    })

    if session:
        message = sign(message, session)

    id_command_map[ident] = command
    await websocket.send(message)
    print(f"> {message}")
    await asyncio.sleep(1)

def sign(message, session):
    private_key = session[0]

    signature = private_key.sign(message.encode(), encoding='base64')
    signature = signature.decode()
    message = json.dumps({ 'payload': message, 'signature': signature })
    return message

async def main():
    session = []
    async with websockets.connect('ws://localhost:8765') as websocket:
        asyncio.create_task(show_replies(websocket))
        while True:
            await poll(websocket, session)

async def show_replies(websocket):
    async for reply in websocket:
        reply = json.loads(reply)

        if 'event' in reply:
            print(f'< {reply}')
            continue

        assert 'id' in reply

        if reply['error'] is not None:
            print('Error (#%s):' % reply['id'], reply['error'])
            continue

        command = id_command_map[reply['id']]
        process_reply(command, reply)

def process_reply(command, reply):
    result = reply['result']
    if command == 'login':
        print(f"< {reply}")
    elif command == 'register':
        print(f"< {reply}")
    elif command == 'fetch_orderbook':
        buy = []
        sell = []

        for order in result:
            price, amount, order_type, timestamp = (
                order['price'], order['amount'], order['order_type'],
                order['timestamp'])
            price = D(price)
            amount = D(amount)
            timestamp = str(timestamp)
            assert order_type == 'Buy' or order_type == 'Sell'
            if order_type == 'Buy':
                buy.append((price, amount, timestamp))
            elif order_type == 'Sell':
                sell.append((price, amount, timestamp))

        buy.sort(key=lambda row: row[0], reverse=True)
        sell.sort(key=lambda row: row[0], reverse=True)

        rows = []

        for price, amount, timestamp in sell:
            rows.append((colored(price, 'red'), amount, timestamp))
        for price, amount, timestamp in buy:
            rows.append((colored(price, 'green'), amount, timestamp))

        print(tabulate(rows, (
            "Price", "Amount", "Time")))
    elif command == 'fetch_trades':
        rows = [(row['price'], row['amount'], row['timestamp'])
                for row in result]
        print(tabulate(rows, (
            "Price", "Amount", "Time")))
    elif command == 'say_hello':
        print(f"< {reply}")
    elif command == 'ticker_info':
        print('Low: ', result['low_price'])
        print('High: ', result['high_price'])
        print('Open: ', result['open_price'])
        print('Close: ', result['close_price'])
    elif command == 'place_order':
        print(f"< {reply}")
    elif command == 'fetch_accounts':
        for row in result:
            code, balance = row['currency_code'], row['balance']
            print(balance, code)
    elif command == 'get_bitcoin_deposit_address':
        print('Address:', result)

async def poll(websocket, session):
    print()
    print('Nonauth commands:')
    print('  [1] Login')
    print('  [2] Register')
    print('  [3] Show orderbook')
    print('  [4] Show trades')
    print('  [5] Ticker')
    print('Auth commands:')
    print('  [6] Say hello')
    print('  [7] Place order')
    print('  [8] Show accounts')
    print('  [9] Bitcoin deposit address')
    print('  [10] Withdraw Bitcoin')

    choice = int(await aioconsole.ainput('> '))

    if choice == 1:
        await login(websocket, session)
    elif choice == 2:
        await register(websocket, session)
    elif choice == 3:
        await show_orderbook(websocket, session)
    elif choice == 4:
        await show_trades(websocket, session)
    elif choice == 5:
        await ticker(websocket, session)
    elif choice == 6:
        await say_hello(websocket, session)
    elif choice == 7:
        await place_order(websocket, session)
    elif choice == 8:
        await show_accounts(websocket, session)
    elif choice == 9:
        await bitcoin_address(websocket, session)
    elif choice == 10:
        await withdraw_bitcoin(websocket, session)

async def login(websocket, session):
    assert not session

    username = await aioconsole.ainput('Username: ')
    password = await aioconsole.ainput('Password: ')

    private_key, public_key = ed25519.create_keypair()
    session_key = public_key.to_ascii(encoding="hex").decode()

    await send(websocket, session, 'login', [username, password, session_key])

    session.append(private_key)

async def register(websocket, session):
    assert not session

    username = await aioconsole.ainput('Username: ')
    email = await aioconsole.ainput('Email: ')
    password = await aioconsole.ainput('Password: ')

    await send(websocket, session, 'register', [username, email, password])

async def show_orderbook(websocket, session):
    base = (await aioconsole.ainput('Base: ')).upper()
    quote = (await aioconsole.ainput('Quote: ')).upper()

    await send(websocket, session, 'fetch_orderbook', [base, quote])

async def show_trades(websocket, session):
    base = (await aioconsole.ainput('Base: ')).upper()
    quote = (await aioconsole.ainput('Quote: ')).upper()

    await send(websocket, session, 'fetch_trades', [base, quote])

async def ticker(websocket, session):
    base = (await aioconsole.ainput('Base: ')).upper()
    quote = (await aioconsole.ainput('Quote: ')).upper()

    await send(websocket, session, 'ticker_info', [base, quote])

async def say_hello(websocket, session):
    await send(websocket, session, 'say_hello', ['hello'])

async def place_order(websocket, session):
    base = (await aioconsole.ainput('Base: ')).upper()
    quote = (await aioconsole.ainput('Quote: ')).upper()
    price = await aioconsole.ainput('Price: ')
    amount = await aioconsole.ainput('Amount: ')
    print('Order type:')
    print('  [1] Buy')
    print('  [2] Sell')
    order_type = int(await aioconsole.ainput('> '))

    if order_type == 1:
        order_type = 'Buy'
    else:
        order_type = 'Sell'

    await send(websocket, session, 'place_order', [
        base, quote, price, amount, order_type])

async def show_accounts(websocket, session):
    await send(websocket, session, 'fetch_accounts', [])

async def bitcoin_address(websocket, session):
    await send(websocket, session, 'get_bitcoin_deposit_address', [])

async def withdraw_bitcoin(websocket, session):
    address = await aioconsole.ainput('Address: ')
    amount = await aioconsole.ainput('Amount: ')

    await send(websocket, session, 'withdraw_bitcoin', [address, amount])

asyncio.get_event_loop().run_until_complete(main())
