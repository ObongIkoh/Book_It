import logging
from app.core.config import settings # Import the settings instance

# Define a public function for configuring logging
def configure_logging():
    """
    Configures the root logging handler based on application settings.
    """
    # CRITICAL FIX: Use settings.log_level (lowercase) to match app/core/config.py
    log_level = settings.log_level.upper()
    
    # Apply standard library configuration
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    
    # Optionally quiet down noisy third-party loggers
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Log success
    logger = logging.getLogger("bookit.utils.logging")
    logger.info(f"Root logger configured to level: {log_level}")
