from sqlalchemy import Column, Enum, Integer, String, Boolean, Float, ForeignKey, DateTime, Numeric, Text, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base
import enum


class BookingStatus(enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    cancelled = "cancelled"
    completed = "completed"


class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default='user')  # roles: user, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    bookings = relationship("Booking", back_populates="user")
    

class Service(Base):
    __tablename__ = 'services'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    title = Column(String(50), index=True, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    duration_minutes = Column(Integer, nullable=False)  # Duration of the service in minutes
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)
    
    bookings = relationship("Booking", back_populates="service")
    

class Booking(Base):
    __tablename__ = 'bookings'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    service_id = Column(UUID(as_uuid=True), ForeignKey('services.id'), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.pending)  # pending|confirmed|cancelled|completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationships
    user = relationship("User", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")
    review = relationship("Review", back_populates="booking", uselist=False, cascade="all, delete-orphan")
    
    # Add indexes for performance
    __table_args__ = (
        {'comment': 'Booking table with UUID primary keys'}
    )


class Review(Base):
    __tablename__ = 'reviews'
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    booking_id = Column(UUID(as_uuid=True), ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False)
    comments = Column(String(500), nullable=True)
    rating = Column(Integer, nullable=False)  # 1 to 5
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    booking = relationship("Booking", back_populates="review")
    

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, nullable=False)  # JWT ID
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    user = relationship("User")
    
    # Add index for performance
    __table_args__ = (
        {'comment': 'Refresh tokens for JWT authentication'}
    )
