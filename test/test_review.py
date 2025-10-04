import pytest
import uuid
from datetime import datetime, timedelta

def test_cannot_review_pending_booking(client, test_user, test_service, db_session):
    """Test that pending bookings cannot be reviewed"""
    from app.db.models import Booking, BookingStatus
    
    # Create a booking directly in DB
    booking = Booking(
        user_id=uuid.UUID(test_user["id"]) if "id" in test_user else uuid.uuid4(),
        service_id=uuid.UUID(test_service["id"]),
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, minutes=60),
        status=BookingStatus.pending
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    
    # Try to review
    response = client.post(
        "/reviews/",
        json={
            "booking_id": str(booking.id),
            "rating": 5,
            "comment": "Great service!"
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 400
    data = response.json()
    assert "completed" in data["message"].lower()

def test_review_completed_booking_success(client, test_user, test_service, db_session):
    """Test successful review of completed booking"""
    from app.db.models import Booking, BookingStatus, User
    
    # Get user from DB
    user = db_session.query(User).filter(User.email == test_user["email"]).first()
    
    # Create completed booking
    booking = Booking(
        user_id=user.id,
        service_id=uuid.UUID(test_service["id"]),
        start_time=datetime.utcnow() - timedelta(days=1),
        end_time=datetime.utcnow() - timedelta(days=1) + timedelta(minutes=60),
        status=BookingStatus.completed
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    
    # Create review
    response = client.post(
        "/reviews/",
        json={
            "booking_id": str(booking.id),
            "rating": 5,
            "comment": "Excellent service!"
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rating"] == 5
    assert data["comment"] == "Excellent service!"

def test_cannot_review_twice(client, test_user, test_service, db_session):
    """Test that same booking cannot be reviewed twice"""
    from app.db.models import Booking, BookingStatus, Review, User
    
    user = db_session.query(User).filter(User.email == test_user["email"]).first()
    
    # Create completed booking with review
    booking = Booking(
        user_id=user.id,
        service_id=uuid.UUID(test_service["id"]),
        start_time=datetime.utcnow() - timedelta(days=2),
        end_time=datetime.utcnow() - timedelta(days=2) + timedelta(minutes=60),
        status=BookingStatus.completed
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    
    review = Review(
        booking_id=booking.id,
        rating=4,
        comment="Good"
    )
    db_session.add(review)
    db_session.commit()
    
    # Try to create another review
    response = client.post(
        "/reviews/",
        json={
            "booking_id": str(booking.id),
            "rating": 5,
            "comment": "Changed my mind!"
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["message"].lower()

def test_rating_validation(client, test_user, test_service, db_session):
    """Test rating must be between 1-5"""
    from app.db.models import Booking, BookingStatus, User
    
    user = db_session.query(User).filter(User.email == test_user["email"]).first()
    
    booking = Booking(
        user_id=user.id,
        service_id=uuid.UUID(test_service["id"]),
        start_time=datetime.utcnow() - timedelta(days=1),
        end_time=datetime.utcnow() - timedelta(days=1) + timedelta(minutes=60),
        status=BookingStatus.completed
    )
    db_session.add(booking)
    db_session.commit()
    db_session.refresh(booking)
    
    # Test rating too high
    response = client.post(
        "/reviews/",
        json={
            "booking_id": str(booking.id),
            "rating": 6,
            "comment": "Too high"
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 422  # Pydantic validation
    
    # Test rating too low
    response = client.post(
        "/reviews/",
        json={
            "booking_id": str(booking.id),
            "rating": 0,
            "comment": "Too low"
        },
        headers={"Authorization": f"Bearer {test_user['access_token']}"}
    )
    assert response.status_code == 422
