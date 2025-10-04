import pytest

def test_refresh_token_success(client, test_user):
    """Test successful token refresh"""
    response = client.post("/auth/refresh", json={
        "refresh_token": test_user["refresh_token"]
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_refresh_token_missing(client):
    """Test refresh without token"""
    # Missing field should trigger Pydantic 422 validation error
    response = client.post("/auth/refresh", json={})
    assert response.status_code == 422
    # NOTE: Asserting status code 400 here previously was incorrect if Pydantic raises 422 first.

def test_refresh_token_invalid(client):
    """Test refresh with invalid token"""
    response = client.post("/auth/refresh", json={
        "refresh_token": "invalid_token"
    })
    assert response.status_code == 401

def test_logout_success(client, test_user):
    """Test successful logout"""
    # Assuming logout invalidates the refresh token (e.g., marks it as revoked in DB)
    response = client.post("/auth/logout", json={
        "refresh_token": test_user["refresh_token"]
    })
    assert response.status_code == 204

def test_logout_then_refresh_fails(client, test_user):
    """Test that refresh fails after logout"""
    # Logout first
    logout_response = client.post("/auth/logout", json={
        "refresh_token": test_user["refresh_token"]
    })
    assert logout_response.status_code == 204
    
    # Try to refresh with revoked token
    refresh_response = client.post("/auth/refresh", json={
        "refresh_token": test_user["refresh_token"]
    })
    # --- COMPLETED LOGIC ---
    assert refresh_response.status_code == 401
    # --- END COMPLETED LOGIC ---
