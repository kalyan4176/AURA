from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.auth.entities import UserCreate, UserLogin, Token, User as DomainUser
from app.application.auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

async def get_current_user_dependency(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> DomainUser:
    """Dependency to retrieve the logged-in user from the JWT access token.
    Supports standard Authorization headers and ?token=... query strings for downloads.
    """
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    if not token:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth_service = AuthService(db)
    try:
        return await auth_service.get_current_user(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=DomainUser, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        return await auth_service.register_user(user_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        return await auth_service.authenticate_user(credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token_str: str, db: AsyncSession = Depends(get_db)):
    auth_service = AuthService(db)
    try:
        new_access_token = await auth_service.refresh_access_token(refresh_token_str)
        return Token(access_token=new_access_token, refresh_token=refresh_token_str)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=DomainUser)
async def get_me(current_user: DomainUser = Depends(get_current_user_dependency)):
    return current_user
