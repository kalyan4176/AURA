from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.domain.auth.entities import UserCreate, UserLogin, Token, User as DomainUser
from app.infrastructure.repositories.postgres_repository import UserRepository
from app.core import security


class AuthService:
    """Manages User credentials, logins, registration, and RBAC token provisioning."""

    def __init__(self, session: AsyncSession):
        self.repo = UserRepository(session)

    async def register_user(self, user_in: UserCreate) -> DomainUser:
        """Register a new user after verifying that the email is unique."""
        existing_user = await self.repo.get_by_email(user_in.email)
        if existing_user:
            logger.warning(f"Registration attempt failed: Email {user_in.email} already exists.")
            raise ValueError("Email already registered")

        hashed_password = security.get_password_hash(user_in.password)
        db_user = await self.repo.create(user_in, hashed_password)
        logger.info(f"User {db_user.email} registered successfully with role {db_user.role}.")
        
        return DomainUser.model_validate(db_user)

    async def authenticate_user(self, credentials: UserLogin) -> Token:
        """Authenticate user and return a Token payload (Access & Refresh JWTs)."""
        db_user = await self.repo.get_by_email(credentials.email)
        if not db_user:
            logger.warning(f"Authentication failed: User {credentials.email} not found.")
            raise ValueError("Incorrect email or password")

        if not db_user.is_active:
            raise ValueError("User account is inactive")

        if not security.verify_password(credentials.password, db_user.hashed_password):
            logger.warning(f"Authentication failed: Wrong password for user {credentials.email}.")
            raise ValueError("Incorrect email or password")

        access_token = security.create_access_token(subject=str(db_user.id))
        refresh_token = security.create_refresh_token(subject=str(db_user.id))

        logger.info(f"User {db_user.email} logged in successfully.")
        return Token(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, refresh_token: str) -> str:
        """Issue a new access token from a valid refresh token."""
        try:
            payload = security.decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise ValueError("Invalid token type")
            
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid subject claim")

            # Create access token
            return security.create_access_token(subject=user_id)
        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise ValueError("Invalid refresh token") from e
            
    async def get_current_user(self, token: str) -> DomainUser:
        """Resolve current active user context from JWT."""
        try:
            payload = security.decode_token(token)
            if payload.get("type") != "access":
                raise ValueError("Invalid token type")
            
            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Token sub claim missing")
                
            db_user = await self.repo.get_by_id(user_id)
            if not db_user or not db_user.is_active:
                raise ValueError("User inactive or not found")
                
            return DomainUser.model_validate(db_user)
        except Exception as e:
            logger.warning(f"Failed decoding auth user from token: {e}")
            raise ValueError("Could not validate credentials") from e
