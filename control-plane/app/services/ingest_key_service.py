import secrets
import uuid

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.organization_ingest_key import OrganizationIngestKey


class IngestKeyService:
    @staticmethod
    def hash_key(raw_key: str) -> str:
        payload = f"{settings.ingest_key_pepper}:{raw_key}".encode("utf-8")
        return bcrypt.hashpw(payload, bcrypt.gensalt(rounds=12)).decode("utf-8")

    @staticmethod
    def get_org_key(db: Session, org_id: uuid.UUID) -> OrganizationIngestKey | None:
        return db.scalar(select(OrganizationIngestKey).where(OrganizationIngestKey.org_id == org_id))

    @staticmethod
    def rotate_org_key(db: Session, org_id: uuid.UUID) -> tuple[str, OrganizationIngestKey]:
        plaintext_key = secrets.token_urlsafe(36)
        key_hash = IngestKeyService.hash_key(plaintext_key)
        record = IngestKeyService.get_org_key(db, org_id)
        if record:
            record.key_hash = key_hash
        else:
            record = OrganizationIngestKey(org_id=org_id, key_hash=key_hash)
            db.add(record)
        db.commit()
        db.refresh(record)
        return plaintext_key, record
