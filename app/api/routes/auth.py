from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import TokenSchema, LoginSchema,SignupSchema
from app.schemas.schemas import UserCreate,UserResponse
from app.schemas.user import UserSchema
from app.api.deps.auth import get_current_active_user


router = APIRouter(prefix="/auth", tags=["auth"])
print("Auth router module loaded")
# Refresh schema for request body
class RefreshSchema(BaseModel):
    refresh_token: str


@router.post("/signup", response_model=UserResponse)
async def signup(data: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await AuthService.create_user(
            db,
           data
        )
        print("User created:", user.email)  # 👈 important
        return user
    except Exception as e:
        print("SIGNUP ERROR:", e)  # 👈 important
        raise

@router.post("/login", response_model=TokenSchema)
async def login(form_data:  OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return AuthService.generate_tokens(user)

@router.post("/refresh", response_model=TokenSchema)
async def refresh(data: RefreshSchema):
    user_id = AuthService.validate_refresh_token(data.refresh_token)
    return {
        "access_token": AuthService.create_access_token(user_id),
        "refresh_token": data.refresh_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
async def get_me(user=Depends(get_current_active_user)):
    return user