from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, schemas, auth
from .connection_manager import manager
import json

ws_router = APIRouter()

@ws_router.websocket("/ws/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: str,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    try:
        current_user_data = auth.get_current_user(token=token, db=db)
        username = current_user_data["username"]
        role = current_user_data["role"]
        authenticated_room_id = current_user_data["room_id"]

        room = crud.get_room_by_id(db, room_id)
        if not room:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Room not found.")
            return

        if role == "user" and room_id != authenticated_room_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Not authorized to access this room.")
            return

        await manager.connect(websocket, room_id)
        print(f"User {username} ({role}) connected to WebSocket for room {room_id}")
        await manager.send_personal_message(json.dumps({"type": "info", "message": f"Connected to room {room_id} as {username} ({role})."}), websocket)

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    message_data = json.loads(data)
                    sender_role_from_client = message_data.get("sender")
                    content = message_data.get("content")

                    if not sender_role_from_client or not content:
                        await manager.send_personal_message(json.dumps({"type": "error", "message": "Invalid message format. Requires 'sender' and 'content'."}), websocket)
                        continue

                    if sender_role_from_client != role:
                        await manager.send_personal_message(json.dumps({"type": "error", "message": "Sender role mismatch with authenticated role."}), websocket)
                        continue

                    message_to_create = schemas.MessageCreate(room_id=room_id, sender=role, content=content)
                    db_message = crud.create_message(db, message_to_create)
                    
                    response_message = schemas.MessageResponse.model_validate(db_message).model_dump_json()
                    await manager.broadcast_to_room(response_message, room_id)

                except json.JSONDecodeError:
                    await manager.send_personal_message(json.dumps({"type": "error", "message": "Message must be a valid JSON string."}), websocket)
                except Exception as e:
                    print(f"Error processing websocket message: {e}")
                    await manager.send_personal_message(json.dumps({"type": "error", "message": f"Server error: {e}"}), websocket)

        except WebSocketDisconnect:
            manager.disconnect(websocket, room_id)
            print(f"User {username} ({role}) disconnected from room {room_id}")
        except Exception as e:
            print(f"Unexpected error in websocket_endpoint inner loop for {username}: {e}")
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=f"An unexpected error occurred: {e}")

    except HTTPException as e:
        print(f"WebSocket authentication error for room {room_id}: {e.detail}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason=e.detail)
    except Exception as e:
        print(f"Unexpected error during WebSocket connection setup for room {room_id}: {e}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason=f"An unexpected error occurred during setup: {e}")