from typing import Literal, Optional


from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Full name of the user"
    )

    email: EmailStr = Field(
        ...,
        description="Valid email address"
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password"
    )


class UserLogin(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Registered email address"
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password"
    )


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=1)
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Updated user name"
    )

    email: Optional[EmailStr] = Field(
        None,
        description="Updated email address"
    )


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: Literal["user", "admin"]


class UserRoleUpdate(BaseModel):
    role: Literal["user", "admin"]