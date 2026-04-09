"""
HUNTER.OS - Test Configuration
SQLite in-memory database for fast, isolated tests.
Uses StaticPool to ensure all connections share the same in-memory DB.
"""
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app as fastapi_app
from app.models.user import User
from app.core.security import create_access_token, hash_password as get_password_hash

# Import ALL models so Base.metadata knows about them
from app.models import lead, product, campaign, message, lead_product  # noqa: F401
from app.models import account, refresh_token, audit_log, linkedin_guard_state  # noqa: F401

app = fastapi_app

# In-memory SQLite with StaticPool — single shared connection
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after. Reset rate limiters."""
    # Ensure clean state: drop first, then create
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Reset rate limiters to avoid cross-test state leakage
    from app.core.rate_limiter import (
        login_rate_limiter, register_rate_limiter, login_attempt_tracker,
    )
    for limiter in [login_rate_limiter, register_rate_limiter]:
        instance = limiter._get()
        if hasattr(instance, "_requests"):
            instance._requests.clear()
    tracker = login_attempt_tracker._get()
    if hasattr(tracker, "_attempts"):
        tracker._attempts.clear()

    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Provide a clean database session for each test."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """FastAPI test client with DB dependency override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db) -> User:
    """Create a test user and return it."""
    user = User(
        email="test@hunter.os",
        full_name="Test User",
        hashed_password=get_password_hash("testpass123"),
        plan="pro",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Return auth headers with a valid JWT token."""
    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}
