from src.api.auth import hash_password, verify_password, create_access_token, verify_token, user_manager
from src.api.billing import create_checkout_session


def test_password_hashing():
    raw_password = "supersecretpassword123"
    hashed = hash_password(raw_password)
    
    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False


def test_jwt_token_creation_and_verification():
    data = {"sub": "developer@example.com", "user_id": "usr_123", "tier": "pro"}
    token = create_access_token(data, expires_in=3600)
    
    assert isinstance(token, str)
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "developer@example.com"
    assert payload["tier"] == "pro"


def test_user_manager_registration_and_login():
    email = "user1@example.com"
    pwd = "password123"
    
    user = user_manager.register_user(email, pwd, "Test Developer")
    assert user["email"] == email
    assert user["tier"] == "free"
    
    auth_user = user_manager.authenticate_user(email, pwd)
    assert auth_user is not None
    assert auth_user["email"] == email
    
    invalid_auth = user_manager.authenticate_user(email, "badpassword")
    assert invalid_auth is None


def test_billing_checkout_session():
    session = create_checkout_session(user_id="usr_123", tier="pro")
    
    assert "session_id" in session
    assert "checkout_url" in session
    assert session["price"] == 19
    assert session["tier"] == "pro"
