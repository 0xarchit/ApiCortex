"""API and endpoint service for CRUD operations and monitoring configuration."""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api import API
from app.models.endpoint import Endpoint
from app.schemas.api import APICreate, APIUpdate, EndpointCreate, EndpointUpdate
from app.services.timescale_cleanup_service import TimescaleCleanupService


class APIService:
    """Service for managing APIs and their endpoints."""
    @staticmethod
    def list_apis(db: Session, org_id: uuid.UUID) -> list[API]:
        """List all APIs for an organization.
        
        Args:
            db: Database session.
            org_id: Organization UUID.
            
        Returns:
            List of API objects ordered by creation date (newest first).
        """
        return list(db.scalars(select(API).where(API.org_id == org_id).order_by(API.created_at.desc())).all())

    @staticmethod
    def create_api(db: Session, org_id: uuid.UUID, payload: APICreate) -> API:
        """Create a new API and default root endpoint.
        
        Args:
            db: Database session.
            org_id: Organization UUID.
            payload: API creation data (name, base_url).
            
        Returns:
            Created API object.
        """
        api = API(org_id=org_id, name=payload.name, base_url=str(payload.base_url))
        db.add(api)
        db.flush()

        endpoint = Endpoint(
            api_id=api.id,
            org_id=org_id,
            path="/",
            method="GET",
            monitoring_enabled=True,
        )
        db.add(endpoint)

        db.commit()
        db.refresh(api)
        return api

    @staticmethod
    def update_api(db: Session, org_id: uuid.UUID, api_id: uuid.UUID, payload: APIUpdate) -> API:
        """Update an API's name or base URL.
        
        Args:
            db: Database session.
            org_id: Organization UUID.
            api_id: API UUID.
            payload: Update data (name and/or base_url).
            
        Returns:
            Updated API object.
            
        Raises:
            ValueError: If API not found in organization.
        """
        api = db.scalar(select(API).where(API.id == api_id, API.org_id == org_id))
        if not api:
            raise ValueError("API not found")

        if payload.name is not None:
            api.name = payload.name
        if payload.base_url is not None:
            api.base_url = str(payload.base_url)

        db.add(api)
        db.commit()
        db.refresh(api)
        return api

    @staticmethod
    def delete_api(db: Session, org_id: uuid.UUID, api_id: uuid.UUID) -> None:
        """Delete an API and all associated telemetry/prediction data.
        
        Args:
            db: Database session.
            org_id: Organization UUID.
            api_id: API UUID.
            
        Raises:
            ValueError: If API not found in organization.
            RuntimeError: If telemetry cleanup fails.
        """
        api = db.scalar(select(API).where(API.id == api_id, API.org_id == org_id))
        if not api:
            raise ValueError("API not found")

        try:
            TimescaleCleanupService.delete_api_data(org_id=org_id, api_id=api_id)
        except Exception as exc:
            raise RuntimeError("Failed to clean up API telemetry and predictions") from exc

        db.delete(api)
        db.commit()

    @staticmethod
    def create_endpoint(db: Session, org_id: uuid.UUID, api_id: uuid.UUID, payload: EndpointCreate) -> Endpoint:
        """Create a new endpoint for an API.
        
        Args:
            db: Database session.
            org_id: Organization UUID.
            api_id: API UUID.
            payload: Endpoint creation data (path, method, poll settings, etc.).
            
        Returns:
            Created Endpoint object.
            
        Raises:
            ValueError: If API not found, endpoint already exists, or invalid parameters.
        """
        api = db.scalar(select(API).where(API.id == api_id, API.org_id == org_id))
        if not api:
            raise ValueError("API not found")
        method = payload.method.upper()
        poll_interval_seconds = payload.poll_interval_seconds
        timeout_ms = payload.timeout_ms
        if poll_interval_seconds is not None and poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be > 0")
        if timeout_ms is not None and timeout_ms <= 0:
            raise ValueError("timeout_ms must be > 0")
        exists = db.scalar(
            select(Endpoint).where(
                Endpoint.api_id == api_id,
                Endpoint.path == payload.path,
                Endpoint.method == method,
                Endpoint.org_id == org_id,
            )
        )
        if exists:
            raise ValueError("Duplicate endpoint path + method for API")
        endpoint = Endpoint(
            api_id=api_id,
            org_id=org_id,
            path=payload.path,
            method=method,
            monitoring_enabled=payload.monitoring_enabled,
            poll_interval_seconds=poll_interval_seconds,
            timeout_ms=timeout_ms,
            poll_headers_json=payload.poll_headers_json,
        )
        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)
        return endpoint

    @staticmethod
    def list_endpoints(db: Session, org_id: uuid.UUID, api_id: uuid.UUID) -> list[Endpoint]:
        return list(
            db.scalars(select(Endpoint).where(Endpoint.org_id == org_id, Endpoint.api_id == api_id).order_by(Endpoint.created_at.desc())).all()
        )

    @staticmethod
    def update_endpoint(db: Session, org_id: uuid.UUID, endpoint_id: uuid.UUID, payload: EndpointUpdate) -> Endpoint:
        endpoint = db.scalar(select(Endpoint).where(Endpoint.id == endpoint_id, Endpoint.org_id == org_id))
        if not endpoint:
            raise ValueError("Endpoint not found")

        path = payload.path if payload.path is not None else endpoint.path
        method = payload.method.upper() if payload.method is not None else endpoint.method

        if payload.poll_interval_seconds is not None and payload.poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be > 0")
        if payload.timeout_ms is not None and payload.timeout_ms <= 0:
            raise ValueError("timeout_ms must be > 0")

        if path != endpoint.path or method != endpoint.method:
            exists = db.scalar(
                select(Endpoint).where(
                    Endpoint.api_id == endpoint.api_id,
                    Endpoint.path == path,
                    Endpoint.method == method,
                    Endpoint.org_id == org_id,
                    Endpoint.id != endpoint.id,
                )
            )
            if exists:
                raise ValueError("Duplicate endpoint path + method for API")

        endpoint.path = path
        endpoint.method = method
        if payload.monitoring_enabled is not None:
            endpoint.monitoring_enabled = payload.monitoring_enabled
        if payload.poll_interval_seconds is not None:
            endpoint.poll_interval_seconds = payload.poll_interval_seconds
        if payload.timeout_ms is not None:
            endpoint.timeout_ms = payload.timeout_ms
        if payload.poll_headers_json is not None:
            endpoint.poll_headers_json = payload.poll_headers_json

        db.add(endpoint)
        db.commit()
        db.refresh(endpoint)
        return endpoint

    @staticmethod
    def delete_endpoint(db: Session, org_id: uuid.UUID, endpoint_id: uuid.UUID) -> None:
        endpoint = db.scalar(select(Endpoint).where(Endpoint.id == endpoint_id, Endpoint.org_id == org_id))
        if not endpoint:
            raise ValueError("Endpoint not found")
        db.delete(endpoint)
        db.commit()
