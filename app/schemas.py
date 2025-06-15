from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class RoomBase(BaseModel):
    username: str

class RoomCreate(RoomBase):
    password: str

class RoomResponse(RoomBase):
    id: str

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    sender: str
    content: str

class MessageCreate(MessageBase):
    room_id: str

class MessageResponse(MessageBase):
    id: int
    room_id: str
    timestamp: datetime

    class Config:
        from_attributes = True

class AdminMessageCreate(BaseModel):
    room_id: str 
    content: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserLoginResponse(BaseModel):
    access_token: str
    token_type: str
    room_id: str
    username: str
    role: str

class AdminRoomSummary(BaseModel):
    id: str
    username: str
    last_message_content: Optional[str] = None
    last_message_timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True