from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.db.models import Booking, Service, User
from app.core.exceptions import DatabaseError, NotFoundError, ValidationError, ConflictError
from datetime import datetime, timezone
from typing import List, Optional
import logging
import uuid

logger = logging.getLogger(__name__)

class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, booking: Booking) -> Booking:
        """Create new booking with error handling"""
        try:
            self.db.add(booking)
            self.db.commit()
            self.db.refresh(booking)
            logger.info(f"Booking created successfully: {booking.id} for user {booking.user_id}")
            return booking
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity error creating booking: {e}")
            if "user_id" in str(e.orig).lower():
                raise ValidationError("Invalid user ID")
            elif "service_id" in str(e.orig).lower():
                raise ValidationError("Invalid service ID")
            else:
                raise ValidationError("Booking data conflicts with existing records")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating booking: {e}")
            raise DatabaseError("Failed to create booking")

    def create_from_dict(self, data: dict) -> Booking:
        """Create booking from dictionary with validation"""
        try:
            # Validate required fields
            required_fields = ['user_id', 'service_id', 'start_time', 'end_time']
            missing_fields = [field for field in required_fields if field not in data or data[field] is None]
            if missing_fields:
                raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Validate user exists
            user = self.db.query(User).filter(User.id == data['user_id']).first()
            if not user:
                raise ValidationError("User not found")
            
            # Validate service exists and is active
            service = self.db.query(Service).filter(Service.id == data['service_id']).first()
            if not service:
                raise ValidationError("Service not found")
            if not service.is_active:
                raise ValidationError("Service is not available for booking")
            
            # Validate datetime fields
            start_time = data['start_time']
            end_time = data['end_time']
            
            if not isinstance(start_time, datetime) or not isinstance(end_time, datetime):
                raise ValidationError("Start time and end time must be datetime objects")
            
            if start_time >= end_time:
                raise ValidationError("Start time must be before end time")
            
            if start_time < datetime.now(timezone.utc):
                raise ValidationError("Cannot book appointments in the past")
            
            # Check for booking conflicts
            conflicts = self.find_overlapping_bookings(
                service_id=data['service_id'],
                start_time=start_time,
                end_time=end_time
            )
            if conflicts:
                raise ConflictError("Time slot conflicts with existing booking")
            
            booking = Booking(**data)
            return self.create(booking)
            
        except (ValidationError, ConflictError):
            raise
        except Exception as e:
            logger.error(f"Error creating booking from data: {e}")
            raise DatabaseError("Failed to create booking")

    def get_by_id(self, booking_id: uuid.UUID) -> Booking | None:
        """Get booking by ID with error handling - fixed to use int"""
        try:
            return self.db.query(Booking).filter(Booking.id == booking_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting booking by ID {booking_id}: {e}")
            raise DatabaseError("Failed to retrieve booking")

    def get_by_id_or_404(self, booking_id: int) -> Booking:
        """Get booking by ID or raise NotFoundError"""
        booking = self.get_by_id(booking_id)
        if not booking:
            raise NotFoundError("Booking")
        return booking

    def get_all(self, 
                user_id: uuid.UUID = None, 
                admin: bool = False, 
                status: str = None,
                from_date: datetime = None,
                to_date: datetime = None) -> List[Booking]:
        """Get bookings with filters and error handling - fixed to use int"""
        try:
            query = self.db.query(Booking)
            
            # Filter by user if not admin
            if not admin and user_id:
                query = query.filter(Booking.user_id == user_id)
            
            # Filter by status
            if status:
                valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
                if status not in valid_statuses:
                    raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
                query = query.filter(Booking.status == status)
            
            # Filter by date range
            if from_date:
                query = query.filter(Booking.start_time >= from_date)
            if to_date:
                query = query.filter(Booking.end_time <= to_date)
            
            return query.order_by(Booking.start_time.desc()).all()
            
        except ValidationError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Database error getting bookings: {e}")
            raise DatabaseError("Failed to retrieve bookings")

    def get_user_bookings(self, user_id: int) -> List[Booking]:
        """Get all bookings for a specific user"""
        try:
            return self.db.query(Booking).filter(
                Booking.user_id == user_id
            ).order_by(Booking.start_time.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting user bookings: {e}")
            raise DatabaseError("Failed to retrieve user bookings")

    def find_overlapping_bookings(self, 
                                service_id: int, 
                                start_time: datetime, 
                                end_time: datetime,
                                exclude_booking_id: int = None) -> List[Booking]:
        """Find bookings that overlap with the given time range - CRITICAL for conflict detection"""
        try:
            query = self.db.query(Booking).filter(
                Booking.service_id == service_id,
                Booking.status.in_(['pending', 'confirmed']),  # Only active bookings
                Booking.start_time < end_time,  # Booking starts before our end
                Booking.end_time > start_time   # Booking ends after our start
            )
            
            # Exclude specific booking (useful for updates)
            if exclude_booking_id:
                query = query.filter(Booking.id != exclude_booking_id)
            
            overlaps = query.all()
            
            if overlaps:
                logger.warning(f"Found {len(overlaps)} overlapping bookings for service {service_id}")
            
            return overlaps
            
        except SQLAlchemyError as e:
            logger.error(f"Database error finding overlapping bookings: {e}")
            raise DatabaseError("Failed to check booking conflicts")

    def update(self, booking: Booking, data: dict) -> Booking:
        """Update booking with error handling and conflict checking"""
        try:
            # Filter out None values and empty strings
            filtered_data = {k: v for k, v in data.items() if v is not None and v != ""}
            
            # Validate updatable fields
            valid_fields = {'start_time', 'end_time', 'status'}
            invalid_fields = set(filtered_data.keys()) - valid_fields
            if invalid_fields:
                logger.warning(f"Attempted to update invalid fields: {invalid_fields}")
                filtered_data = {k: v for k, v in filtered_data.items() if k in valid_fields}
            
            # Validate status transitions
            if 'status' in filtered_data:
                new_status = filtered_data['status']
                valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
                if new_status not in valid_statuses:
                    raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
                
                # Business rules for status transitions
                current_status = booking.status
                if current_status == 'completed' and new_status != 'completed':
                    raise ValidationError("Cannot change status of completed booking")
                if current_status == 'cancelled' and new_status not in ['cancelled']:
                    raise ValidationError("Cannot reactivate cancelled booking")
            
            # If updating time, check for conflicts
            if 'start_time' in filtered_data or 'end_time' in filtered_data:
                new_start = filtered_data.get('start_time', booking.start_time)
                new_end = filtered_data.get('end_time', booking.end_time)
                
                if new_start >= new_end:
                    raise ValidationError("Start time must be before end time")
                
                if new_start < datetime.utcnow():
                    raise ValidationError("Cannot reschedule to past time")
                
                # Check for conflicts (excluding current booking)
                conflicts = self.find_overlapping_bookings(
                    service_id=booking.service_id,
                    start_time=new_start,
                    end_time=new_end,
                    exclude_booking_id=booking.id
                )
                if conflicts:
                    raise ConflictError("New time slot conflicts with existing booking")
            
            # Apply updates
            for key, value in filtered_data.items():
                setattr(booking, key, value)
            
            self.db.commit()
            self.db.refresh(booking)
            logger.info(f"Booking updated successfully: {booking.id}")
            return booking
            
        except (ValidationError, ConflictError):
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating booking {booking.id}: {e}")
            raise DatabaseError("Failed to update booking")

    def delete(self, booking: Booking) -> bool:
        """Delete booking with error handling and validation"""
        try:
            # Business rule: Only allow deletion of future bookings
            if booking.start_time <= datetime.utcnow():
                raise ValidationError("Cannot delete booking that has already started")
            
            # Business rule: Only allow deletion of non-completed bookings
            if booking.status == 'completed':
                raise ValidationError("Cannot delete completed booking")
            
            self.db.delete(booking)
            self.db.commit()
            logger.info(f"Booking deleted successfully: {booking.id}")
            return True
            
        except ValidationError:
            raise
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting booking {booking.id}: {e}")
            raise DatabaseError("Failed to delete booking")

    def cancel_booking(self, booking: Booking) -> Booking:
        """Cancel booking (safer than deletion)"""
        if booking.status in ['completed', 'cancelled']:
            raise ValidationError(f"Cannot cancel {booking.status} booking")
        
        return self.update(booking, {'status': 'cancelled'})

    def get_upcoming_bookings(self, user_id: int = None, days_ahead: int = 30) -> List[Booking]:
        """Get upcoming bookings within specified days"""
        try:
            from_date = datetime.now(timezone.utc)
            to_date = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)

            # Add days
            from datetime import timedelta
            to_date = to_date + timedelta(days=days_ahead)
            
            query = self.db.query(Booking).filter(
                Booking.start_time >= from_date,
                Booking.start_time <= to_date,
                Booking.status.in_(['pending', 'confirmed'])
            )
            
            if user_id:
                query = query.filter(Booking.user_id == user_id)
            
            return query.order_by(Booking.start_time).all()
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting upcoming bookings: {e}")
            raise DatabaseError("Failed to retrieve upcoming bookings")

    def get_bookings_by_service(self, service_id: int) -> List[Booking]:
        """Get all bookings for a specific service"""
        try:
            return self.db.query(Booking).filter(
                Booking.service_id == service_id
            ).order_by(Booking.start_time.desc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error getting service bookings: {e}")
            raise DatabaseError("Failed to retrieve service bookings")