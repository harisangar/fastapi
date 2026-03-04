

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError
from app.schemas.schemas import UserCreate

from app.db.models.all_models import User
from app.core.security.password import verify_password,hash_password
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    get_user_id_from_payload,
    TokenType,
)


class AuthService:
    """
    Handles authentication logic:
    - Login
    - Token generation
    - Token validation
    """

    # =========================
    # LOGIN
    # =========================
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> User | None:
        """
        Validate email + password.
        Returns user if valid, else None.
        """
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if not user.status == "active":
            return None

        return user

    # =========================
    # TOKEN ISSUING
    # =========================
    @staticmethod
    def generate_tokens(user: User) -> dict:
        """
        Generate access + refresh tokens for user.
        """
        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    # =========================
    # REFRESH FLOW
    # =========================
    @staticmethod
    def validate_refresh_token(token: str) -> str:
        """
        Validate refresh token and return user_id.
        """
        try:
            payload = decode_token(token)
            verify_token_type(payload, TokenType.REFRESH)
            user_id = get_user_id_from_payload(payload)
            return user_id
        except JWTError:
            raise ValueError("Invalid refresh token")

    # =========================
    # ACCESS TOKEN VALIDATION
    # =========================
    @staticmethod
    def validate_access_token(token: str) -> str:
        """
        Validate access token and return user_id.
        """
        try:
            payload = decode_token(token)
            verify_token_type(payload, TokenType.ACCESS)
            user_id = get_user_id_from_payload(payload)
            return user_id
        except JWTError:
            raise ValueError("Invalid access token")
        
    @staticmethod
    async def create_user(db: AsyncSession, user_data: UserCreate) -> User:
        print("Creating user with email:", user_data.email)  # 👈 important
        # Check if user exists
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError("User already exists")
        hashed_pass = hash_password(user_data.password)
        user = User(
        username=user_data.username,
        email=user_data.email,
        phone=user_data.phone,
        password_hash=hashed_pass,
        role=user_data.role,
        designation=user_data.designation,
        department=user_data.department,
        employee_id=user_data.employee_id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user