from uuid import UUID
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional


class UserRole(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class User(BaseModel):
    id: Optional[UUID] = None
    email: EmailStr
    is_active: bool = True
    role: UserRole = UserRole.VIEWER

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Optional[UserRole] = UserRole.VIEWER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
