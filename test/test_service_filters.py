import pytest

def test_list_services_no_filter(client, test_service):
    """Test listing all services"""
    response = client.get("/services/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_filter_services_by_price(client, test_admin):
    """Test filtering services by price range"""
    # Create services with different prices
    client.post("/services/", json={
        "title": "Cheap Service",
        "price": 30.0,
        "duration_minutes": 30,
        "is_active": True
    }, headers={"Authorization": f"Bearer {test_admin['access_token']}"})
    
    client.post("/services/", json={
        "title": "Expensive Service",
        "price": 200.0,
        "duration_minutes": 90,
        "is_active": True
    }, headers={"Authorization": f"Bearer {test_admin['access_token']}"})
    
    # Filter by price
    response = client.get("/services/?price_min=50&price_max=150")
    assert response.status_code == 200
    data = response.json()
    for service in data:
        assert 50 <= service["price"] <= 150

def test_filter_services_by_active(client, test_admin, test_service):
    """Test filtering by active status"""
    # Deactivate a service
    client.patch(
        f"/services/{test_service['id']}",
        json={"is_active": False},
        headers={"Authorization": f"Bearer {test_admin['access_token']}"}
    )
    
    # Get only active services
    response = client.get("/services/?is_active=true")
    assert response.status_code == 200
    data = response.json()
    for service in data:
        assert service["is_active"] is True

def test_search_services_by_title(client, test_service):
    """Test searching services by title"""
    response = client.get("/services/?q=massage")
    assert response.status_code == 200
    data = response.json()
    for service in data:
        assert "massage" in service["title"].lower()
