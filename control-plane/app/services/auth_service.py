"""Authentication service for user and organization management."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User


class AuthService:
    """Service for handling user authentication and organization membership."""
    @staticmethod
    def get_or_create_user(db: Session, email: str, name: str, provider: str) -> User:
        """Get or create a user by email, updating name and provider if needed.
        
        Args:
            db: Database session.
            email: User email address.
            name: User display name.
            provider: OAuth provider (e.g., "google", "github").
            
        Returns:
            User object.
        """
        user = db.scalar(select(User).where(User.email == email))
        if user:
            if user.name != name or user.provider != provider:
                user.name = name
                user.provider = provider
                db.add(user)
                db.commit()
                db.refresh(user)
            return user
        user = User(email=email, name=name, provider=provider)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def ensure_default_org_membership(db: Session, user: User) -> tuple[Organization, Membership]:
        """Ensure user has at least one organization membership.
        
        Creates default organization and membership if user has none.
        
        Args:
            db: Database session.
            user: User object.
            
        Returns:
            Tuple of (Organization, Membership).
        """
        membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
        if membership:
            org = db.get(Organization, membership.org_id)
            return org, membership
        org = Organization(name=f"{user.name}'s Organization", plan="free")
        db.add(org)
        db.flush()
        membership = Membership(user_id=user.id, org_id=org.id, role="owner")
        db.add(membership)
        db.commit()
        db.refresh(org)
        db.refresh(membership)
        return org, membership

    @staticmethod
    def get_user_org_membership(db: Session, user_id: uuid.UUID, org_id: uuid.UUID) -> tuple[Organization, Membership]:
        """Get user's membership in a specific organization.
        
        Args:
            db: Database session.
            user_id: User UUID.
            org_id: Organization UUID.
            
        Returns:
            Tuple of (Organization, Membership).
            
        Raises:
            ValueError: If membership or organization not found.
        """
        membership = db.scalar(select(Membership).where(Membership.user_id == user_id, Membership.org_id == org_id))
        if not membership:
            raise ValueError("Membership not found")
        org = db.get(Organization, org_id)
        if not org:
            raise ValueError("Organization not found")
        return org, membership
