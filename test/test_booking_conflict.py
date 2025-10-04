import pytest
import uuid
from datetime import datetime, timedelta

def test_create_booking_success(client, test_user, test_service):
    """Test successful booking creation"""
    # Use timezone-aware datetime or handle ISO formatting carefully if your backend requires TZs
    start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    
    response = client.post(
        "/bookings/",
        json={
            "service_id": test_service["id"],
            "start_time": start_time
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["service_id"] == test_service["id"]
    assert data["status"] == "pending"

def test_booking_conflict(client, test_user, test_service):
    """Test that overlapping bookings are rejected"""
    start_time = (datetime.utcnow() + timedelta(days=2)).isoformat()
    
    # Create first booking
    response1 = client.post(
        "/bookings/",
        json={
            "service_id": test_service["id"],
            "start_time": start_time
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response1.status_code == 201
    
    # Try to create overlapping booking (30 minutes into first booking)
    # The service duration is 60 minutes (from test_service fixture)
    overlap_time = (datetime.fromisoformat(start_time) + timedelta(minutes=30)).isoformat()
    response2 = client.post(
        "/bookings/",
        json={
            "service_id": test_service["id"],
            "start_time": overlap_time
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response2.status_code == 409
    data = response2.json()
    assert "conflict" in data["message"].lower()

def test_booking_past_time_rejected(client, test_user, test_service):
    """Test that booking in the past is rejected"""
    past_time = (datetime.utcnow() - timedelta(days=1)).isoformat()
    
    response = client.post(
        "/bookings/",
        json={
            "service_id": test_service["id"],
            "start_time": past_time
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    # Assuming your backend raises a 400 for business logic errors like invalid time
    assert response.status_code == 400
    data = response.json()
    assert "past" in data["message"].lower() or "future" in data["message"].lower()

def test_booking_nonexistent_service(client, test_user):
    """Test booking non-existent service fails"""
    # Ensure the fake UUID is correct format but won't exist
    fake_uuid = str(uuid.uuid4()) 
    start_time = (datetime.utcnow() + timedelta(days=1)).isoformat()
    
    response = client.post(
        "/bookings/",
        json={
            "service_id": fake_uuid,
            "start_time": start_time
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    # Expecting 404 Not Found if the service lookup fails, or 400 if validation catches a generic foreign key issue
    assert response.status_code in [404, 400]

def test_cancelled_booking_not_conflict(client, test_user, test_service):
    """Test that cancelled bookings don't cause conflicts"""
    start_time = (datetime.utcnow() + timedelta(days=3)).isoformat()
    
    # Create booking
    response1 = client.post(
        "/bookings/",
        json={
            "service_id": test_service["id"],
            "start_time": start_time
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response1.status_code == 201
    booking_id = response1.json()["id"]
    
    # Cancel booking
    cancel_response = client.patch(
        f"/bookings/{booking_id}",
        json={"status": "cancelled"},
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert cancel_response.status_code == 200
    
    # Now same time slot should be available
    response2 = client.post(
        "/bookings/",
        json={
            "service_id": test_service["id"],
            "start_time": start_time
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    # --- COMPLETED LOGIC ---
    assert response2.status_code == 201
    assert response2.json()["status"] == "pending"
    # --- END COMPLETED LOGIC ---
