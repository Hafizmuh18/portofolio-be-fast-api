from sqlalchemy.orm import Session
from sqlalchemy import desc
from . import models, schemas
from .auth import hash_password, verify_password

def get_room_by_username(db: Session, username: str):
    return db.query(models.Room).filter(models.Room.username == username).first()

def get_room_by_id(db: Session, room_id: str):
    return db.query(models.Room).filter(models.Room.id == room_id).first()

def create_room(db: Session, room: schemas.RoomCreate):
    hashed_password = hash_password(room.password)
    db_room = models.Room(username=room.username, password=hashed_password)
    db.add(db_room)
    db.commit()
    db.refresh(db_room)
    return db_room

def get_all_rooms_summary(db: Session):
    rooms = db.query(models.Room).all()
    summaries = []
    for room in rooms:
        last_message = db.query(models.Message)\
                         .filter(models.Message.room_id == room.id)\
                         .order_by(desc(models.Message.timestamp))\
                         .first()
        summary = schemas.AdminRoomSummary(
            id=room.id,
            username=room.username,
            last_message_content=last_message.content if last_message else None,
            last_message_timestamp=last_message.timestamp if last_message else None
        )
        summaries.append(summary)
    return summaries

def get_messages_by_room_id(db: Session, room_id: str):
    return db.query(models.Message).filter(models.Message.room_id == room_id).order_by(models.Message.timestamp).all()

def create_message(db: Session, message: schemas.MessageCreate):
    db_message = models.Message(**message.model_dump())
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def get_all_messages(db: Session):
    return db.query(models.Message).order_by(models.Message.timestamp).all()