from sqlalchemy.orm import Session
from app.repositories.service_repo import ServiceRepository
from app.db.models import Service, User
from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    DatabaseError
)
import uuid
import logging

logger = logging.getLogger(__name__)

class ServiceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ServiceRepository(db)

    def get(self, service_id: uuid.UUID) -> Service:
        """Get service by ID"""
        try:
            service = self.repo.get_by_id(service_id)
            if not service:
                raise NotFoundError("Service")
            return service
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting service {service_id}: {e}")
            raise DatabaseError("Failed to retrieve service")

    def list(self, 
             q: str = None, 
             price_min: float = None, 
             price_max: float = None, 
             is_active: bool = None,
             duration_min: int = None,
             duration_max: int = None):
        """List services with filters"""
        try:
            # Validate price range
            if price_min is not None and price_min < 0:
                raise ValidationError("Minimum price cannot be negative")
            if price_max is not None and price_max < 0:
                raise ValidationError("Maximum price cannot be negative")
            if price_min is not None and price_max is not None and price_max < price_min:
                raise ValidationError("Maximum price must be greater than or equal to minimum price")
            
            # Validate duration range
            if duration_min is not None and duration_min < 0:
                raise ValidationError("Minimum duration cannot be negative")
            if duration_max is not None and duration_max < 0:
                raise ValidationError("Maximum duration cannot be negative")
            if duration_min is not None and duration_max is not None and duration_max < duration_min:
                raise ValidationError("Maximum duration must be greater than or equal to minimum duration")
            
            return self.repo.list(
                q=q,
                price_min=price_min,
                price_max=price_max,
                active=is_active
            )
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            raise DatabaseError("Failed to retrieve services")

    def get_active_services(self):
        """Get only active services"""
        try:
            return self.repo.get_active_services()
        except Exception as e:
            logger.error(f"Error getting active services: {e}")
            raise DatabaseError("Failed to retrieve active services")

    def search(self, search_term: str):
        """Search services by title"""
        try:
            if not search_term or len(search_term.strip()) == 0:
                raise ValidationError("Search term cannot be empty")
            return self.repo.search_by_title(search_term.strip())
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Error searching services: {e}")
            raise DatabaseError("Failed to search services")

    def create(self, title: str, description: str, price: float, duration_minutes: int, 
               is_active: bool, current_user: User) -> Service:
        """Create a new service (admin only)"""
        try:
            # Check admin permission
            if current_user.role != "admin":
                raise AuthorizationError("Only administrators can create services")
            
            # Validate required fields
            if not title or len(title.strip()) == 0:
                raise ValidationError("Service title is required")
            
            if len(title) > 255:
                raise ValidationError("Service title cannot exceed 255 characters")
            
            # Validate price
            if not isinstance(price, (int, float)):
                raise ValidationError("Price must be a number")
            if price <= 0:
                raise ValidationError("Price must be greater than 0")
            
            # Validate duration
            if not isinstance(duration_minutes, int):
                raise ValidationError("Duration must be an integer")
            if duration_minutes <= 0:
                raise ValidationError("Duration must be greater than 0")
            if duration_minutes > 1440:  # 24 hours
                raise ValidationError("Duration cannot exceed 24 hours (1440 minutes)")
            
            # Create service
            service_data = {
                'title': title.strip(),
                'description': description.strip() if description else None,
                'price': round(price, 2),
                'duration_minutes': duration_minutes,
                'is_active': is_active if is_active is not None else True
            }
            
            service = self.repo.create_from_dict(service_data)
            logger.info(f"Service created successfully: {service.title} by admin {current_user.id}")
            return service
            
        except (ValidationError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            raise DatabaseError("Failed to create service")

    def update(self, service_id: uuid.UUID, title: str = None, description: str = None, 
               price: float = None, duration_minutes: int = None, is_active: bool = None,
               current_user: User = None) -> Service:
        """Update a service (admin only)"""
        try:
            # Check admin permission
            if current_user.role != "admin":
                raise AuthorizationError("Only administrators can update services")
            
            # Get service
            service = self.repo.get_by_id(service_id)
            if not service:
                raise NotFoundError("Service")
            
            # Prepare update data
            update_data = {}
            
            # Validate and add title
            if title is not None:
                if len(title.strip()) == 0:
                    raise ValidationError("Service title cannot be empty")
                if len(title) > 255:
                    raise ValidationError("Service title cannot exceed 255 characters")
                update_data['title'] = title.strip()
            
            # Validate and add price
            if price is not None:
                if not isinstance(price, (int, float)):
                    raise ValidationError("Price must be a number")
                if price <= 0:
                    raise ValidationError("Price must be greater than 0")
                update_data['price'] = round(price, 2)
            
            # Validate and add duration
            if duration_minutes is not None:
                if not isinstance(duration_minutes, int):
                    raise ValidationError("Duration must be an integer")
                if duration_minutes <= 0:
                    raise ValidationError("Duration must be greater than 0")
                if duration_minutes > 1440:
                    raise ValidationError("Duration cannot exceed 24 hours (1440 minutes)")
                update_data['duration_minutes'] = duration_minutes
            
            # Add description
            if description is not None:
                update_data['description'] = description.strip() if description else None
            
            # Add is_active
            if is_active is not None:
                update_data['is_active'] = is_active
            
            if not update_data:
                raise ValidationError("No valid fields to update")
            
            updated_service = self.repo.update(service, update_data)
            logger.info(f"Service {service_id} updated by admin {current_user.id}")
            return updated_service
            
        except (ValidationError, NotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error updating service {service_id}: {e}")
            raise DatabaseError("Failed to update service")

    def delete(self, service_id: uuid.UUID, current_user: User) -> bool:
        """Delete a service (admin only)"""
        try:
            # Check admin permission
            if current_user.role != "admin":
                raise AuthorizationError("Only administrators can delete services")
            
            # Get service
            service = self.repo.get_by_id(service_id)
            if not service:
                raise NotFoundError("Service")
            
            # Check if service has bookings
            # Note: If you have ON DELETE CASCADE, this will delete related bookings
            # Otherwise, you might want to check for active bookings first
            
            # Delete service
            self.repo.delete(service)
            logger.info(f"Service {service_id} deleted by admin {current_user.id}")
            return True
            
        except (NotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error deleting service {service_id}: {e}")
            raise DatabaseError("Failed to delete service")

    def toggle_active(self, service_id: uuid.UUID, current_user: User) -> Service:
        """Toggle service active status (admin only)"""
        try:
            # Check admin permission
            if current_user.role != "admin":
                raise AuthorizationError("Only administrators can modify service status")
            
            # Get service
            service = self.repo.get_by_id(service_id)
            if not service:
                raise NotFoundError("Service")
            
            # Toggle active status
            new_status = not service.is_active
            updated_service = self.repo.update(service, {'is_active': new_status})
            
            logger.info(f"Service {service_id} active status changed to {new_status} by admin {current_user.id}")
            return updated_service
            
        except (NotFoundError, AuthorizationError):
            raise
        except Exception as e:
            logger.error(f"Error toggling service status {service_id}: {e}")
            raise DatabaseError("Failed to update service status")