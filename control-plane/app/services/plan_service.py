"""Plan and feature flag service for quota and capability management."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.api import API
from app.models.feature_flag import FeatureFlag


class PlanService:
    """Service for managing organization plans and API quota limits."""
    limits = {
        "free": 1,
        "pro": 10,
        "business": None,
    }

    @classmethod
    def resolve_api_quota_limit(cls, db: Session, plan: str) -> int | None:
        """Resolve the API quota limit for a plan.
        
        Checks for dynamic feature flags first, then falls back to static limits.
        
        Args:
            db: Database session.
            plan: Plan name ("free", "pro", "business", etc.).
            
        Returns:
            API quota limit as integer, or None for unlimited.
        """
        normalized_plan = (plan or "free").lower()
        dynamic_limit = db.scalar(
            select(FeatureFlag.limit).where(
                FeatureFlag.plan == normalized_plan,
                FeatureFlag.feature_key == "api_quota",
                FeatureFlag.enabled.is_(True),
            )
        )
        if dynamic_limit is not None:
            return int(dynamic_limit)
        return cls.limits.get(normalized_plan, 1)

    @classmethod
    def check_api_quota(cls, db: Session, org_id: uuid.UUID, plan: str) -> bool:
        """Check if organization is under API quota limit.
        
        Args:
            db: Database session.
            org_id: Organization UUID.
            plan: Organization plan name.
            
        Returns:
            True if under limit, False if at/over limit.
        """
        limit = cls.resolve_api_quota_limit(db, plan)
        if limit is None:
            return True
        count = db.scalar(select(func.count(API.id)).where(API.org_id == org_id)) or 0
        return count < limit
