from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import logging

from app.repositories.booking_repo import BookingRepository
from app.repositories.service_repo import ServiceRepository
from app.db.models import Booking, BookingStatus
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    ConflictError,
    DatabaseError
)

logger = logging.getLogger(__name__)

class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.booking_repo = BookingRepository(db)
        self.service_repo = ServiceRepository(db)

    def create_booking(
        self, 
        user_id: uuid.UUID, 
        service_id: uuid.UUID, 
        start_time: datetime
    ) -> Booking:
        """
        Create a new booking with conflict detection
        
        Args:
            user_id: UUID of the user making the booking
            service_id: UUID of the service to book
            start_time: Start time of the booking
        
        Returns:
            Created Booking object
        
        Raises:
            ValidationError: If booking data is invalid
            NotFoundError: If service doesn't exist
            ConflictError: If time slot conflicts with existing booking
        """
        try:
            # Validate start time is in the future
            if start_time <= datetime.utcnow():
                raise ValidationError("Booking start time must be in the future")
            
            # Get service and validate it exists and is active
            service = self.service_repo.get_by_id(service_id)
            if not service:
                raise NotFoundError("Service")
            
            if not service.is_active:
                raise ValidationError("Service is not available for booking")
            
            # Calculate end time based on service duration
            end_time = start_time + timedelta(minutes=service.duration_minutes)
            
            # Check for booking conflicts
            conflicts = self.booking_repo.find_overlapping_bookings(
                service_id=service_id,
                start_time=start_time,
                end_time=end_time
            )
            
            if conflicts:
                raise ConflictError(
                    f"Time slot conflicts with existing booking. "
                    f"Service is unavailable from {start_time} to {end_time}"
                )
            
            # Create booking
            booking_data = {
                'user_id': user_id,
                'service_id': service_id,
                'start_time': start_time,
                'end_time': end_time,
                'status': BookingStatus.pending
            }
            
            booking = self.booking_repo.create_from_dict(booking_data)
            logger.info(f"Booking created: {booking.id} for user {user_id}, service {service_id}")
            return booking
            
        except (ValidationError, NotFoundError, ConflictError):
            raise
        except Exception as e:
            logger.error(f"Error creating booking: {e}")
            raise DatabaseError("Failed to create booking")

    def list_bookings(
        self,
        user_id: Optional[uuid.UUID] = None,
        is_admin: bool = False,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Booking]:
        """
        List bookings with filters
        
        Args:
            user_id: Filter by user (required for non-admin users)
            is_admin: Whether the requester is an admin
            status: Filter by booking status
            from_date: Filter bookings from this date
            to_date: Filter bookings until this date
        
        Returns:
            List of Booking objects
        """
        try:
            return self.booking_repo.get_all(
                user_id=user_id,
                admin=is_admin,
                status=status,
                from_date=from_date,
                to_date=to_date
            )
        except Exception as e:
            logger.error(f"Error listing bookings: {e}")
            raise DatabaseError("Failed to retrieve bookings")

    def get_booking(
        self, 
        booking_id: uuid.UUID, 
        user_id: uuid.UUID, 
        is_admin: bool = False
    ) -> Booking:
        """
        Get a specific booking by ID
        
        Args:
            booking_id: UUID of the booking
            user_id: UUID of the requesting user
            is_admin: Whether the requester is an admin
        
        Returns:
            Booking object
        
        Raises:
            NotFoundError: If booking doesn't exist
            AuthorizationError: If user doesn't have permission
        """
        try:
            booking = self.booking_repo.get_by_id(booking_id)
            if not booking:
                raise NotFoundError("Booking")
            
            # Check authorization (admin or owner)
            if not is_admin and booking.user_id != user_id:
                raise AuthorizationError("You can only view your own bookings")
            
            return booking
            
        except (NotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error getting booking {booking_id}: {e}")
            raise DatabaseError("Failed to retrieve booking")

    def update_booking(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False,
        start_time: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> Booking:
        """
        Update a booking (reschedule or change status)
        
        Args:
            booking_id: UUID of the booking to update
            user_id: UUID of the requesting user
            is_admin: Whether the requester is an admin
            start_time: New start time (for rescheduling)
            status: New status
        
        Returns:
            Updated Booking object
        
        Raises:
            NotFoundError: If booking doesn't exist
            AuthorizationError: If user doesn't have permission
            ValidationError: If update is not allowed
            ConflictError: If new time slot conflicts
        """
        try:
            # Get booking
            booking = self.booking_repo.get_by_id(booking_id)
            if not booking:
                raise NotFoundError("Booking")
            
            # Check authorization
            if not is_admin and booking.user_id != user_id:
                raise AuthorizationError("You can only update your own bookings")
            
            update_data = {}
            
            # Handle status update
            if status:
                if is_admin:
                    # Admins can set any status
                    valid_statuses = [s.value for s in BookingStatus]
                    if status not in valid_statuses:
                        raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
                    update_data['status'] = status
                else:
                    # Users can only cancel their own bookings
                    if status == BookingStatus.cancelled.value:
                        if booking.status in [BookingStatus.pending.value, BookingStatus.confirmed.value]:
                            update_data['status'] = status
                        else:
                            raise ValidationError(f"Cannot cancel booking with status: {booking.status}")
                    else:
                        raise AuthorizationError("Only admins can change booking status (except cancellation)")
            
            # Handle rescheduling
            if start_time:
                if booking.status not in [BookingStatus.pending.value, BookingStatus.confirmed.value]:
                    raise ValidationError(f"Cannot reschedule booking with status: {booking.status}")
                
                if start_time <= datetime.utcnow():
                    raise ValidationError("New booking time must be in the future")
                
                # Get service for duration
                service = self.service_repo.get_by_id(booking.service_id)
                if not service:
                    raise NotFoundError("Service")
                
                new_end_time = start_time + timedelta(minutes=service.duration_minutes)
                
                # Check for conflicts (excluding current booking)
                conflicts = self.booking_repo.find_overlapping_bookings(
                    service_id=booking.service_id,
                    start_time=start_time,
                    end_time=new_end_time,
                    exclude_booking_id=booking_id
                )
                
                if conflicts:
                    raise ConflictError("New time slot conflicts with existing booking")
                
                update_data['start_time'] = start_time
                update_data['end_time'] = new_end_time
            
            if not update_data:
                raise ValidationError("No valid fields to update")
            
            # Update booking
            updated_booking = self.booking_repo.update(booking, update_data)
            logger.info(f"Booking {booking_id} updated by {'admin' if is_admin else f'user {user_id}'}")
            return updated_booking
            
        except (NotFoundError, AuthorizationError, ValidationError, ConflictError):
            raise
        except Exception as e:
            logger.error(f"Error updating booking {booking_id}: {e}")
            raise DatabaseError("Failed to update booking")

    def delete_booking(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
        is_admin: bool = False
    ) -> bool:
        """
        Delete a booking
        
        Args:
            booking_id: UUID of the booking to delete
            user_id: UUID of the requesting user
            is_admin: Whether the requester is an admin
        
        Returns:
            True if deleted successfully
        
        Raises:
            NotFoundError: If booking doesn't exist
            AuthorizationError: If user doesn't have permission
            ValidationError: If deletion is not allowed
        """
        try:
            # Get booking
            booking = self.booking_repo.get_by_id(booking_id)
            if not booking:
                raise NotFoundError("Booking")
            
            # Check authorization
            if not is_admin and booking.user_id != user_id:
                raise AuthorizationError("You can only delete your own bookings")
            
            # Business rules for deletion
            if not is_admin:
                # Users can only delete future bookings
                if booking.start_time <= datetime.utcnow():
                    raise ValidationError("Cannot delete bookings that have already started")
                
                # Users cannot delete completed bookings
                if booking.status == BookingStatus.completed.value:
                    raise ValidationError("Cannot delete completed bookings")
            
            # Delete booking
            self.booking_repo.delete(booking)
            logger.info(f"Booking {booking_id} deleted by {'admin' if is_admin else f'user {user_id}'}")
            return True
            
        except (NotFoundError, AuthorizationError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Error deleting booking {booking_id}: {e}")
            raise DatabaseError("Failed to delete booking")

    def cancel_booking(self, booking_id: uuid.UUID, user_id: uuid.UUID) -> Booking:
        """
        Cancel a booking (safer than deletion)
        
        Args:
            booking_id: UUID of the booking to cancel
            user_id: UUID of the user
        
        Returns:
            Cancelled Booking object
        """
        return self.update_booking(
            booking_id=booking_id,
            user_id=user_id,
            is_admin=False,
            status=BookingStatus.cancelled.value
        )

    def get_upcoming_bookings(
        self, 
        user_id: uuid.UUID, 
        days_ahead: int = 30
    ) -> List[Booking]:
        """
        Get upcoming bookings for a user
        
        Args:
            user_id: UUID of the user
            days_ahead: Number of days to look ahead (default 30)
        
        Returns:
            List of upcoming Booking objects
        """
        try:
            return self.booking_repo.get_upcoming_bookings(
                user_id=user_id,
                days_ahead=days_ahead
            )
        except Exception as e:
            logger.error(f"Error getting upcoming bookings for user {user_id}: {e}")
            raise DatabaseError("Failed to retrieve upcoming bookings")

    def get_bookings_by_service(self, service_id: uuid.UUID) -> List[Booking]:
        """
        Get all bookings for a specific service (admin only)
        
        Args:
            service_id: UUID of the service
        
        Returns:
            List of Booking objects
        """
        try:
            return self.booking_repo.get_bookings_by_service(service_id)
        except Exception as e:
            logger.error(f"Error getting bookings for service {service_id}: {e}")
            raise DatabaseError("Failed to retrieve service bookings")

    def get_booking_statistics(self, user_id: Optional[uuid.UUID] = None) -> dict:
        """
        Get booking statistics
        
        Args:
            user_id: Optional user ID to get user-specific stats
        
        Returns:
            Dictionary with booking statistics
        """
        try:
            if user_id:
                bookings = self.booking_repo.get_user_bookings(user_id)
            else:
                bookings = self.booking_repo.get_all(admin=True)
            
            total = len(bookings)
            by_status = {}
            for status in BookingStatus:
                by_status[status.value] = len([b for b in bookings if b.status == status])
            
            return {
                'total_bookings': total,
                'by_status': by_status,
                'pending': by_status.get(BookingStatus.pending.value, 0),
                'confirmed': by_status.get(BookingStatus.confirmed.value, 0),
                'completed': by_status.get(BookingStatus.completed.value, 0),
                'cancelled': by_status.get(BookingStatus.cancelled.value, 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting booking statistics: {e}")
            raise DatabaseError("Failed to retrieve booking statistics")