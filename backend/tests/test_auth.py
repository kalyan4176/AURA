import pytest
from app.domain.auth.entities import UserCreate, UserLogin, UserRole
from app.application.auth.services import AuthService


@pytest.mark.asyncio
async def test_user_registration_and_login(db_session):
    auth_service = AuthService(db_session)

    # 1. Register user
    user_in = UserCreate(
        email="test_analyst@aura.ai",
        password="super_secure_password_123",
        role=UserRole.ANALYST
    )
    domain_user = await auth_service.register_user(user_in)
    
    assert domain_user.email == "test_analyst@aura.ai"
    assert domain_user.role == UserRole.ANALYST
    assert domain_user.is_active is True

    # 2. Login successfully
    login_credentials = UserLogin(
        email="test_analyst@aura.ai",
        password="super_secure_password_123"
    )
    tokens = await auth_service.authenticate_user(login_credentials)
    
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None

    # 3. Login with wrong password
    bad_credentials = UserLogin(
        email="test_analyst@aura.ai",
        password="wrong_password"
    )
    with pytest.raises(ValueError, match="Incorrect email or password"):
        await auth_service.authenticate_user(bad_credentials)
