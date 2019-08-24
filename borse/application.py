import asyncio
import json
import websockets

from borse.connection import Connection

class Application:

    def __init__(self, pool):
        self.pool = pool
        self.connections = set()

    async def on_connect(self, websocket, path):
        connection = Connection(self.pool, websocket, self)
        self.connections.add(connection)

        try:
            await connection.start()
        except websockets.exceptions.ConnectionClosed:
            print('Closed.')
        finally:
            self.connections.remove(connection)

    async def broadcast(self, message):
        for connection in self.connections:
            await connection.send(message)

    async def post_events(self):
        while True:
            await asyncio.sleep(1)
            await self.match_orders()
            await self.process_deposits()

    async def match_orders(self):
        async with self.pool.acquire() as db:
            while await self.match_one_order(db):
                pass

    async def match_one_order(self, db):
        trade_data = await db.fetchval('select match_one_order()')
        if trade_data is None:
            return False

        trade_data = json.loads(trade_data)
        notify_message = json.dumps({
            'status': 'ok', 'event': 'trade', 'data': trade_data})
        await self.broadcast(notify_message)
        return True

    async def process_deposits(self):
        async with self.pool.acquire() as db:
            async with db.transaction():
                async for record in db.cursor('''
                    select account_event_id, account_id, amount
                    from account_events
                    where event = 'Deposit' and status = 'Open'
                '''):
                    await self.process_one_deposit(db, *record)

    async def process_one_deposit(self, db, event_id, account_id, amount):
        await db.execute('''
            update accounts
            set balance = balance + $1
            where account_id = $2
        ''', amount, account_id)

        await db.execute('''
            update account_events
            set status = 'Closed'
            where account_event_id = $1
        ''', event_id)

        print('Processed deposit event (%s) to account (%s) for %s' % (
            event_id, account_id, amount))

