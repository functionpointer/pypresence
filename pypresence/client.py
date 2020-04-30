import inspect
import json
import os
from typing import List
import struct
from queue import Queue, Empty
from typing import Union
import sys
import asyncio
import logging

from .payloads import Payload
from .response import Response
from .exceptions import *

class DiscordProtocol(asyncio.Protocol):
    def __init__(self, *args, **kwargs):
        super()
        self.logger = logging.getLogger("DiscordProtocol")
        self._transport = None
        self._events = {} # maps cmd types (like GET_SELECTED_VOICE_CHANNEL) to callback functions. used for events. whenever a message was received and no future in the queue is ready to take it,
                          # we run an event handler from this dict
        self._queues = {} # map from event types to queues # functions that require a response, like get_selected_voice_channel, will enqueue a future here and await it.
                                      # once the response has arrived, the future will be called with the result
        self._errorhandler = print
        self._connection_made_futures = []                                

    def register_event(self, event: str, func: callable):
        self._events[event.lower()] = func

    def unregister_event(self, event: str):
        event = event.lower()
        if event not in self._events:
            raise EventNotFound
        del self._events[event]

    def get_future_for_connection_made(self):
        ret = asyncio.get_running_loop().create_future()
        self._connection_made_futures.append(ret)
        return ret

    def connection_made(self, transport):
        self._transport = transport
        self.logger.info("connection made")
        for f in self._connection_made_futures:
            f.set_result(True)
        self._connection_made_futures = []

    def connection_lost(self, exc):
        self._transport = None
        self.logger.info("connection lost")

    def _message_received(self, status_code, payload):
        cmd = payload["cmd"].lower()
        code = cmd

        response = Response.from_dict(payload, status_code=status_code)

        from_queue = None
        if code in self._queues:
            try:
                from_queue = self._queues[code].get(block=False)
            except Empty:
                pass
        
        if from_queue is not None:
            if payload["evt"] is not None and payload["evt"].lower() == "error":
                self.logger.error("received error payload %s", payload)
                from_queue.set_exception(DiscordError(payload["data"]["code"], payload["data"]["message"]))
            else:
                from_queue.set_result(response)
        
        if cmd=="dispatch":
            if payload["evt"] is None:
                self.logger.warning("dispatch event but no evt code in %s", payload)
                return
            evt = payload["evt"].lower()
            if evt in self._events:
                asyncio.create_task(self._events[evt](response))
            else:
                self.logger.warning("no handler for event %s in payload %s", evt, payload)
        else:
            if from_queue is None:
                self.logger.warning("no handler for message %s", payload)

    def data_received(self, data):
        fmt = '<II'
        header_size = struct.calcsize(fmt)
        while len(data)>header_size:
            status_code, length = struct.unpack(fmt, data[:header_size])
            if len(data)>=length+header_size:
                payload = data[header_size:length+header_size]
                payload = json.loads(payload.decode("utf-8","strict"))
                self._message_received(status_code, payload)
                data = data[length+header_size:]
            else:
                break
        if len(data)>0:
            self.logger.warning("remaining data: %s", data)
            #todo save current state of data and continue processing it on next call

        #messages = [q for q in data.split(b"\x01") if b"cmd" in q]
        #messages = [q[q.find(b"{"):] for q in messages]
        #messages = [q.decode("utf-8","strict") for q in messages]
        #for message in messages:
        #    payload = json.loads(message)
        #    self._message_received(0, payload)

    def get_response(self, cmd_code):
        future = asyncio.get_running_loop().create_future()
        code = cmd_code.lower()
        if code not in self._queues:
            self._queues[code] = Queue()
        self._queues[code].put(future, block=False)
        return future

    def send_data(self, op: int, payload: Union[dict, Payload]):
        #self.logger.debug("sending data %s", payload)
        if isinstance(payload, Payload):
            payload = payload.data
        payload = json.dumps(payload)
        self._transport.write(
            struct.pack(
                '<II',
                op,
                len(payload)) +
            payload.encode('utf-8'))

    def send_data_and_receive_response(self, op: int, payload: Union[dict, Payload]):
        if isinstance(payload, Payload):
            pl = payload.data
        else:
            pl = payload
        response_cmd_code = pl["cmd"]
        future = self.get_response(response_cmd_code)
        self.send_data(op, payload)
        return future

class Client():
    def __init__(self, client_id: str, pipe=0):
        super()
        self.logger = logging.getLogger("DiscordClient")
        self._protocol = None
        self.client_id = client_id

        if sys.platform == 'linux' or sys.platform == 'darwin':
            import tempfile
            tempdir = (os.environ.get('XDG_RUNTIME_DIR') or tempfile.gettempdir())
            snap_path = '{0}/snap.discord'.format(tempdir)
            pipe_file = 'discord-ipc-{0}'.format(pipe)
            if os.path.isdir(snap_path):
                self.ipc_path = '{0}/{1}'.format(snap_path, pipe_file)
            else:
                self.ipc_path = '{0}/{1}'.format(tempdir, pipe_file)
        elif sys.platform == 'win32':
            self.ipc_path = r'\\?\pipe\discord-ipc-' + str(pipe)

    async def start(self):
        loop = asyncio.get_running_loop()
        if sys.platform == 'linux' or sys.platform == 'darwin':
            _, self._protocol = await loop.open_unix_connection(lambda: DiscordProtocol(), self.ipc_path)
        elif sys.platform == 'win32' or sys.platform == 'win64':
            _, self._protocol = await loop.create_pipe_connection(lambda: DiscordProtocol(), self.ipc_path)
        await self._protocol.get_future_for_connection_made()
        await self.handshake()

    async def handshake(self):
        self._protocol.send_data(0, {'v': 1, 'client_id': self.client_id})
        data = await self._protocol.get_response("dispatch")
        self.logger.debug("handshake complete, username is %s", data.user.username)

    async def authorize(self, client_id: str, scopes: List[str]):
        payload = Payload.authorize(client_id, scopes)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def authenticate(self, token: str):
        payload = Payload.authenticate(token)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def get_guilds(self):
        payload = Payload.get_guilds()
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def get_guild(self, guild_id: str):
        payload = Payload.get_guild(guild_id)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def get_channel(self, channel_id: str):
        payload = Payload.get_channel(channel_id)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def get_channels(self, guild_id: str):
        payload = Payload.get_channels(guild_id)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def set_user_voice_settings(self, user_id: str, pan_left: float = None,
                                      pan_right: float = None, volume: int = None,
                                      mute: bool = None):
        payload = Payload.set_user_voice_settings(user_id, pan_left, pan_right, volume, mute)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def select_voice_channel(self, channel_id: str):
        payload = Payload.select_voice_channel(channel_id)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def get_selected_voice_channel(self):
        payload = Payload.get_selected_voice_channel()
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def select_text_channel(self, channel_id: str):
        payload = Payload.select_text_channel(channel_id)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def set_activity(self, pid: int = os.getpid(),
                           state: str = None, details: str = None,
                           start: int = None, end: int = None,
                           large_image: str = None, large_text: str = None,
                           small_image: str = None, small_text: str = None,
                           party_id: str = None, party_size: list = None,
                           join: str = None, spectate: str = None,
                           match: str = None, instance: bool = True):
        payload = Payload.set_activity(pid, state, details, start, end, large_image, large_text,
                                       small_image, small_text, party_id, party_size, join, spectate,
                                       match, instance, activity=True)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def clear_activity(self, pid: int = os.getpid()):
        payload = Payload.set_activity(pid, activity=None)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def register_event(self, event: str, func: callable, args: dict = {}):
        if not inspect.iscoroutinefunction(func):
            raise InvalidArgument('Coroutine', 'Subroutine', 'Event function must be a coroutine')
        elif len(inspect.signature(func).parameters) != 1:
            raise ArgumentError
        self._protocol.register_event(event, func)
        await self._subscribe(event, args)

    async def unregister_event(self, event: str, args: dict = {}):
        self._protocol.unregister_event(event)
        await self._unsubscribe(event, args)

    async def _subscribe(self, event: str, args: dict = {}):
        payload = Payload.subscribe(event, args)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def _unsubscribe(self, event: str, args: dict = {}):
        payload = Payload.unsubscribe(event, args)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def get_voice_settings(self):
        payload = Payload.get_voice_settings()
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def set_voice_settings(self, _input: dict = None, output: dict = None,
                                 mode: dict = None, automatic_gain_control: bool = None,
                                 echo_cancellation: bool = None, noise_suppression: bool = None,
                                 qos: bool = None, silence_warning: bool = None,
                                 deaf: bool = None, mute: bool = None):
        payload = Payload.set_voice_settings(_input, output, mode, automatic_gain_control, echo_cancellation,
                                             noise_suppression, qos, silence_warning, deaf, mute)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def capture_shortcut(self, action: str):
        payload = Payload.capture_shortcut(action)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def send_activity_join_invite(self, user_id: str):
        payload = Payload.send_activity_join_invite(user_id)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def close_activity_request(self, user_id: str):
        payload = Payload.close_activity_request(user_id)
        return await self._protocol.send_data_and_receive_response(1, payload)

    async def close(self):
        self._protocol.send_data(2, {'v': 1, 'client_id': self.client_id})
