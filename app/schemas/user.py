from pydantic import BaseModel, EmailStr
from uuid import UUID

class UserSchema(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    is_active: bool

    model_config = {"from_attributes": True}  # Pydantic v2