from sqlalchemy.orm import Session
from app.db import models
from datetime import datetime, timezone
import uuid

class TokenRepo:
    def __init__(self, db: Session):
        self.db = db

    def create(self, jti: str, user_id: uuid.UUID, expires_at: datetime):
        t = models.RefreshToken(jti=jti, user_id=user_id, expires_at=expires_at)
        self.db.add(t)
        self.db.commit()
        self.db.refresh(t)
        return t

    def revoke(self, jti: str):
        token = self.db.query(models.RefreshToken).filter(models.RefreshToken.jti == jti).first()
        if token:
            token.revoked = True
            self.db.add(token)
            self.db.commit()
        return token

    def is_revoked(self, jti: str):
        token = self.db.query(models.RefreshToken).filter(models.RefreshToken.jti == jti).first()
        return (not token) or token.revoked or token.expires_at <= datetime.now(timezone.utc)

    def get(self, jti: str):
        return self.db.query(models.RefreshToken).filter(models.RefreshToken.jti == jti).first()