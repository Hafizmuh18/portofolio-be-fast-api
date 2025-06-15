import os
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from sqlalchemy.orm import Session
from .database import get_db
from . import crud

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD_HASHED = os.getenv("ADMIN_PASSWORD_HASHED")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_role: str = payload.get("role")
        user_room_id: Optional[str] = payload.get("room_id")

        if username is None or user_role is None:
            raise credentials_exception
        
        if user_role == "user":
            if user_room_id is None:
                raise credentials_exception
            user = crud.get_room_by_username(db, username)
            if user is None or user.id != user_room_id:
                raise credentials_exception
        elif user_role == "admin":
            if username != ADMIN_USERNAME:
                raise credentials_exception
        else:
            raise credentials_exception

        return {"username": username, "role": user_role, "room_id": user_room_id}
    except JWTError:
        raise credentials_exception

async def get_current_admin_user(current_user_data: dict = Depends(get_current_user)):
    if current_user_data["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as admin")
    return current_user_data["username"]

def verify_admin_password(plain_password: str):
    return verify_password(plain_password, ADMIN_PASSWORD_HASHED)