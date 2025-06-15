import os
from dotenv import load_dotenv

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Union 

from .database import get_db, create_db_and_tables
from . import schemas, crud, auth
from .ws.router import ws_router

load_dotenv()

app = FastAPI()
app.include_router(ws_router)

@app.on_event("startup")
def on_startup():
    print("Creating database tables if they don't exist...")
    create_db_and_tables()
    print("Database tables created/checked.")

@app.post("/auth/chat", response_model=schemas.UserLoginResponse)
async def auth_and_enter_chat(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if form_data.username == auth.ADMIN_USERNAME:
        if auth.verify_admin_password(form_data.password):
            access_token = auth.create_access_token(
                data={"sub": form_data.username, "role": "admin", "room_id": None}
            )
            return schemas.UserLoginResponse(
                access_token=access_token,
                token_type="bearer",
                room_id="",
                username=form_data.username,
                role="admin"
            )
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")

    user_room = crud.get_room_by_username(db, form_data.username)

    if user_room:
        if auth.verify_password(form_data.password, user_room.password):
            access_token = auth.create_access_token(
                data={"sub": user_room.username, "role": "user", "room_id": user_room.id}
            )
            return schemas.UserLoginResponse(
                access_token=access_token,
                token_type="bearer",
                room_id=user_room.id,
                username=user_room.username,
                role="user"
            )
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password for user")
    else:
        new_room_data = schemas.RoomCreate(username=form_data.username, password=form_data.password)
        new_room = crud.create_room(db, new_room_data)
        
        access_token = auth.create_access_token(
            data={"sub": new_room.username, "role": "user", "room_id": new_room.id}
        )
        return schemas.UserLoginResponse(
            access_token=access_token,
            token_type="bearer",
            room_id=new_room.id,
            username=new_room.username,
            role="user"
        )

@app.get("/me", response_model=schemas.UserLoginResponse)
async def get_my_info(current_user_data: dict = Depends(auth.get_current_user)):
    return schemas.UserLoginResponse(
        access_token="",
        token_type="bearer",
        room_id=current_user_data["room_id"] if current_user_data["role"] == "user" else "",
        username=current_user_data["username"],
        role=current_user_data["role"]
    )

@app.get("/chat/room/{room_id}/messages", response_model=List[schemas.MessageResponse])
async def get_messages_in_room(
    room_id: str,
    db: Session = Depends(get_db),
    current_user_data: dict = Depends(auth.get_current_user)
):
    if current_user_data["role"] == "user" and room_id != current_user_data["room_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this room's messages.")

    room = crud.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    
    messages = crud.get_messages_by_room_id(db, room_id)
    return messages

@app.post("/chat/message", response_model=schemas.MessageResponse)
async def send_message(
    message_data: schemas.MessageCreate,
    db: Session = Depends(get_db),
    current_user_data: dict = Depends(auth.get_current_user)
):
    if message_data.sender != current_user_data["role"]:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sender role mismatch with authenticated role.")

    if current_user_data["role"] == "user" and message_data.room_id != current_user_data["room_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to send messages to this room.")

    room = crud.get_room_by_id(db, message_data.room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    new_message = crud.create_message(db, message_data)
    return new_message

@app.post("/admin/token", response_model=schemas.Token)
async def admin_login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username == auth.ADMIN_USERNAME and auth.verify_admin_password(form_data.password):
        access_token = auth.create_access_token(
            data={"sub": form_data.username, "role": "admin", "room_id": None}
        )
        return {"access_token": access_token, "token_type": "bearer"}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@app.get("/admin/all_chats", response_model=List[schemas.MessageResponse])
async def get_all_chats_for_admin(
    db: Session = Depends(get_db),
    current_admin_user: str = Depends(auth.get_current_admin_user)
):
    messages = crud.get_all_messages(db)
    return messages

@app.get("/admin/rooms", response_model=List[schemas.AdminRoomSummary])
async def get_all_rooms_summary_for_admin(
    db: Session = Depends(get_db),
    current_admin_user: str = Depends(auth.get_current_admin_user)
):
    rooms_summary = crud.get_all_rooms_summary(db)
    return rooms_summary


@app.post("/admin/reply_message", response_model=schemas.MessageResponse)
async def admin_reply_to_user(
    admin_message_data: schemas.AdminMessageCreate,
    db: Session = Depends(get_db),
    current_admin_user: str = Depends(auth.get_current_admin_user)
):
    room = crud.get_room_by_id(db, admin_message_data.room_id)
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    message_to_create = schemas.MessageCreate(
        room_id=admin_message_data.room_id,
        sender="admin",
        content=admin_message_data.content
    )
    new_message = crud.create_message(db, message_to_create)
    return new_message

@app.get("/")
async def root():
    return JSONResponse(content={"message": "Welcome to the Chat API!"})