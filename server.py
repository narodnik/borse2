import asyncio
import asyncpg
import sys
import websockets

from borse.application import Application

async def setup_database():
    try:
        pool = await asyncpg.create_pool('postgresql://kk@localhost/borse')
    except OSError:
        print('Error: unable to connect to database', file=sys.stderr)
        return None

    return pool

def main():
    pool = asyncio.get_event_loop().run_until_complete(setup_database())
    if pool is None:
        return -1

    app = Application(pool)

    start_server = websockets.serve(app.on_connect, 'localhost', 8765)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_until_complete(app.post_events())
    asyncio.get_event_loop().run_forever()
    return 0

if __name__ == '__main__':
    sys.exit(main())

