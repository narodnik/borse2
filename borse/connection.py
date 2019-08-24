import json

from borse.requests import request_types, authenticated_request_types
from borse.utility import eprint
from borse.verify_signature import PublicKey

def json_parser(message, spec):
    try:
        object_ = json.loads(message)
    except json.JSONDecodeError:
        eprint('invalid json for:', message)
        return None

    if not isinstance(object_, dict):
        eprint('invalid json type for:', message)
        return None

    for key, type_ in spec:
        try:
            value = object_[key]
        except KeyError:
            eprint('missing key for:', message)
            return None

        if not isinstance(value, type_):
            eprint('poorly formed message for:', message)
            return None

    return object_

class Connection:

    def __init__(self, pool, websocket, parent):
        self.pool = pool
        self.websocket = websocket
        self.parent = parent
        self.user_id = None
        self.session_key = None

    async def broadcast(self, status, event, data):
        notify_message = json.dumps({
            'status': status, 'event': event, 'data': data})
        await self.parent.broadcast(notify_message)

    async def start(self):
        async for message in self.websocket:
            print('Received:', message)

            request = self.read_request(message)
            if request is None:
                return

            async with self.pool.acquire() as db:
                response = await request.process(self, db)

            message = json.dumps(response)
            await self.send(message)

    async def send(self, message):
        await self.websocket.send(message)

    def accept_authentication(self, user_id, session_key):
        self.user_id = user_id
        self.session_key = PublicKey(session_key)

    def read_request(self, message):
        payload = self.check_signature(message)
        if payload is None:
            return None
        print('Payload:', payload)

        request = self.parse_request(payload)
        if request is None:
            return None

        return request

    def check_signature(self, message):
        if self.session_key is None:
            return message

        header = json_parser(message, [
            ('payload', str), ('signature', str)])
        if header is None:
            return None

        payload, signature = header['payload'], header['signature']

        if not self.session_key.verify(payload, signature):
            eprint('invalid signature for:', message)
            return None

        return payload

    def parse_request(self, message):
        request = json_parser(message, [
            ('command', str), ('id', int), ('params', list)])
        if request is None:
            return None

        command = request['command']

        if command in request_types:
            return self.make_request_object(request, request_types, message)
        elif command in authenticated_request_types:
            if self.session_key is None:
                eprint('command requires authentication:', message)
                return None
            return self.make_request_object(
                request, authenticated_request_types, message)

        eprint('non-existent command for:', message)
        return None

    def make_request_object(self, request, request_types, message):
        command, ident, params = \
            request['command'], request['id'], request['params']

        request_object = request_types[command](command, ident)
        if not request_object.unpack(params):
            eprint('poorly formed parameters for:', request)
            return None

        return request_object

