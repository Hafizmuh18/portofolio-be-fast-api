from typing import List
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.room_connections: dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        if room_id not in self.room_connections:
            self.room_connections[room_id] = []
        self.room_connections[room_id].append(websocket)
        print(f"WebSocket connected to room {room_id}. Total connections: {len(self.active_connections)}")


    def disconnect(self, websocket: WebSocket, room_id: str):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if room_id in self.room_connections and websocket in self.room_connections[room_id]:
            self.room_connections[room_id].remove(websocket)
            if not self.room_connections[room_id]: 
                del self.room_connections[room_id]
        print(f"WebSocket disconnected from room {room_id}. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_room(self, message: str, room_id: str):
        if room_id in self.room_connections:
            for connection in self.room_connections[room_id]:
                await connection.send_text(message)
        else:
            print(f"No active connections for room {room_id} to broadcast to.")

manager = ConnectionManager()