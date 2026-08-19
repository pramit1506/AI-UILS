import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    full_name: Optional[str] = Field(None, max_length=150)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    role: Optional[str] = Field("user", max_length=50)


class UserLogin(BaseModel):
    login: str = Field(..., description="Email address or username")
    password: str = Field(...)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=150)
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\-\.]+$")
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: Optional[str] = None
    role: str = "user"
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class PasswordResetRequest(BaseModel):
    login: str = Field(..., description="Email address or username of the account to reset")
    new_password: str = Field(..., min_length=6, max_length=100, description="New password")


class AccountDeleteRequest(BaseModel):
    email: EmailStr = Field(..., description="Email address of the account to delete")
    confirm_text: Optional[str] = Field("DELETE", description="Confirmation text to prevent accidental deletion")
