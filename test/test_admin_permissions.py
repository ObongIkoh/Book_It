import pytest
import uuid
from fastapi.testclient import TestClient

# Placeholder for new service data
NEW_SERVICE_DATA = {
    "title": "New Admin Service",
    "description": "Created by Admin for testing",
    "price": 100.0,
    "duration_minutes": 90,
    "is_active": True
}

# --- Admin CRUD Success Tests ---

def test_admin_can_create_service(client: TestClient, test_admin):
    """Admin should successfully create a service (HTTP 201)"""
    response = client.post(
        "/services/",
        json=NEW_SERVICE_DATA,
        headers={"Authorization": f"Bearer {test_admin['access_token']}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == NEW_SERVICE_DATA["title"]
    assert "id" in data

def test_admin_can_update_service(client: TestClient, test_service, test_admin):
    """Admin should successfully update an existing service (HTTP 200)"""
    update_data = {"price": 120.0, "is_active": False}
    
    response = client.patch(
        f"/services/{test_service['id']}",
        json=update_data,
        headers={"Authorization": f"Bearer {test_admin['access_token']}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 120.0
    assert data["is_active"] is False

def test_admin_can_delete_service(client: TestClient, test_admin):
    """Admin should successfully delete a service (HTTP 204)"""
    # 1. Create a service to delete
    create_response = client.post(
        "/services/",
        json=NEW_SERVICE_DATA,
        headers={"Authorization": f"Bearer {test_admin['access_token']}"}
    )
    assert create_response.status_code == 201
    service_id_to_delete = create_response.json()["id"]
    
    # 2. Delete the service
    delete_response = client.delete(
        f"/services/{service_id_to_delete}",
        headers={"Authorization": f"Bearer {test_admin['access_token']}"}
    )
    assert delete_response.status_code == 204
    
    # 3. Verify it's gone
    get_response = client.get(f"/services/{service_id_to_delete}")
    assert get_response.status_code == 404


# --- Regular User Permissions Blockage Tests ---

def test_regular_user_cannot_create_service(client: TestClient, test_user):
    """Regular user should be blocked from creating services (HTTP 403 Forbidden)"""
    response = client.post(
        "/services/",
        json=NEW_SERVICE_DATA,
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 403
    assert "not enough permissions" in response.json()["message"].lower()

def test_regular_user_cannot_update_service(client: TestClient, test_service, test_user):
    """Regular user should be blocked from updating services (HTTP 403 Forbidden)"""
    update_data = {"price": 150.0}
    
    response = client.patch(
        f"/services/{test_service['id']}",
        json=update_data,
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 403
    assert "not enough permissions" in response.json()["message"].lower()

def test_regular_user_cannot_delete_service(client: TestClient, test_service, test_user):
    """Regular user should be blocked from deleting services (HTTP 403 Forbidden)"""
    response = client.delete(
        f"/services/{test_service['id']}",
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 403
    assert "not enough permissions" in response.json()["message"].lower()

def test_regular_user_can_read_services(client: TestClient, test_user):
    """Regular user should be able to list and view services (HTTP 200)"""
    response = client.get(
        "/services/",
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# --- Unauthenticated Access Blockage Tests ---

def test_unauthenticated_cannot_create_service(client: TestClient):
    """Unauthenticated access should fail for creation (HTTP 401 Unauthorized)"""
    response = client.post("/services/", json=NEW_SERVICE_DATA)
    assert response.status_code == 401
    
def test_unauthenticated_cannot_update_service(client: TestClient, test_service):
    """Unauthenticated access should fail for update (HTTP 401 Unauthorized)"""
    response = client.patch(f"/services/{test_service['id']}", json={"price": 500.0})
    assert response.status_code == 401

def test_unauthenticated_cannot_delete_service(client: TestClient, test_service):
    """Unauthenticated access should fail for delete (HTTP 401 Unauthorized)"""
    response = client.delete(f"/services/{test_service['id']}")
    assert response.status_code == 401
