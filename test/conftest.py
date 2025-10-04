import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.models import Base
from app.db.session import get_db
import uuid
from app.services.auth_service import pwd_context # Added import for admin setup
from app.db.models import User # Added import for fetching user ID

# Use SQLite in-memory database for fast tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db_session():
    """Create a fresh database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            # We don't close the session here, as it's handled in db_session fixture rollback
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(client, db_session):
    """Create a test user and return credentials including ID"""
    user_data = {
        "name": "Test User",
        "email": "testuser@example.com",
        "password": "password123"
    }
    # Register user via API
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    
    # Fetch user ID from DB since registration endpoint might not return it
    user_obj = db_session.query(User).filter(User.email == user_data["email"]).first()
    assert user_obj is not None
    
    # Login to get tokens
    login_response = client.post("/auth/login", json={
        "email": user_data["email"],
        "password": user_data["password"]
    })
    assert login_response.status_code == 200
    tokens = login_response.json()
    
    return {
        "id": str(user_obj.id), # Added ID here
        "email": user_data["email"],
        "password": user_data["password"],
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"]
    }

@pytest.fixture
def test_admin(client, db_session):
    """Create an admin user"""
    # NOTE: Moved imports out of fixture definition in general, but kept necessary model imports here.
    
    admin = User(
        name="Admin User",
        email="admin@example.com",
        password_hash=pwd_context.hash("adminpass123"),
        role="admin"
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    # Login to get tokens
    login_response = client.post("/auth/login", json={
        "email": "admin@example.com",
        "password": "adminpass123"
    })
    assert login_response.status_code == 200
    tokens = login_response.json()
    
    return {
        "id": str(admin.id),
        "email": admin.email,
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"]
    }

@pytest.fixture
def test_service(client, test_admin):
    """Create a test service and return its ID and data"""
    service_data = {
        "title": "60-Minute Massage",
        "description": "Relaxing full body massage",
        "price": 89.99,
        "duration_minutes": 60,
        "is_active": True
    }
    response = client.post(
        "/services/",
        json=service_data,
        headers={"Authorization": f"Bearer {test_admin['access_token']}"}
    )
    assert response.status_code == 201
    service_response = response.json()
    
    return {
        "id": service_response["id"],
        "data": service_data
    }
