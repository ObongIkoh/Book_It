import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_validation_errors():
    """Test validation errors during registration"""
    # Missing required fields
    response = client.post("/auth/register", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["error"] is True
    assert "ValidationError" in data["type"]
    assert "details" in data

def test_register_duplicate_email():
    """Test duplicate email registration"""
    # Register first user
    client.post("/auth/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "password123"
    })
    
    # Try to register with same email
    response = client.post("/auth/register", json={
        "name": "Another User",
        "email": "test@example.com",
        "password": "password456"
    })
    assert response.status_code == 409
    data = response.json()
    assert data["error"] is True
    assert "already registered" in data["message"]

def test_login_invalid_credentials():
    """Test login with invalid credentials"""
    response = client.post("/auth/login", json={
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
    data = response.json()
    assert data["error"] is True
    assert "Invalid email or password" in data["message"]

def test_weak_password():
    """Test registration with weak password"""
    response = client.post("/auth/register", json={
        "name": "Test User",
        "email": "test2@example.com",
        "password": "123"  # Too short
    })
    assert response.status_code == 400
    data = response.json()
    assert data["error"] is True
    assert "at least 6 characters" in data["message"]