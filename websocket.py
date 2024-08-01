from fastapi import WebSocket, FastAPI, WebSocketDisconnect
from fastapi.responses import FileResponse
from typing import Any

from schemas.websocket import PublishData
from starlette.middleware.cors import CORSMiddleware
from common import Singleton


class ConnectionManager(metaclass=Singleton):
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, topic: str) -> None:
        await websocket.accept()
        if topic not in self.connections:
            self.connections[topic] = []
        self.connections[topic].append(websocket)
        print(self.connections)

    def disconnect(self, websocket: WebSocket, topic: str) -> None:
        if topic in self.connections:
            self.connections[topic].remove(websocket)
            if not self.connections[topic]:
                del self.connections[topic]

    async def send_message_to_topic(self, topic: str, message: dict[str, Any]) -> None:
        connections = self._get_connections_for_topic(topic)
        if connections:
            await self._send_from_all_connections(connections, message)

    def _get_connections_for_topic(self, topic: str) -> list[WebSocket]:
        connections = []
        for key, conns in self.connections.items():
            if topic == key[:len(topic)] or "#" in key:
                connections.extend(conns)
        return connections

    async def _send_from_all_connections(self, conns: list[WebSocket], message: dict[str, Any]) -> None:
        for conn in conns:
            await conn.send_json(message)



class WebSocketConnection:
    def __init__(self, websocket: WebSocket = None) -> None:
        self._websocket = websocket
        self._connection_manager = ConnectionManager()

    async def subscribe(self, topic: str):
        await self._connection_manager.connect(self._websocket, topic)
        try:
            while True:
                data = await self._websocket.receive_json()
                await self._connection_manager.send_message_to_topic(topic, data)
        except WebSocketDisconnect:
            print("Disconnect")
            self._connection_manager.disconnect(self._websocket, topic)
        except Exception as e:
            print("[WebSocketConnection] Error in real-time websocket: ", e)
            raise

    async def publish_message(self, topic: str, message: dict):
        await self._connection_manager.send_message_to_topic(topic, message)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/')
async def get():
    return FileResponse("templates/index.html")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, topic: str): 
    await WebSocketConnection(websocket=websocket).subscribe(topic=topic)

@app.post("/publish")
async def publish_message(payload: PublishData):
    await WebSocketConnection().publish_message(topic=payload.topic, message=payload.message)
