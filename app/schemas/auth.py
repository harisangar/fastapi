# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class SignupSchema(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None  # optional

    model_config = {"from_attributes": True}
class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"