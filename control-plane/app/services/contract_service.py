import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.api import API, Endpoint
from app.models.job import Job
from app.models.openapi_spec import Contract, OpenAPISpec
from app.schemas.api import ContractCreate, OpenAPIUploadRequest, OpenAPISpecCreate
from app.services.plan_service import PlanService


class ContractService:
    @staticmethod
    def upload_openapi_with_api_resolution(
        db: Session,
        org_id: uuid.UUID,
        payload: OpenAPIUploadRequest,
        plan: str,
    ) -> tuple[OpenAPISpec, API, bool, int]:
        api_created = False
        api: API | None = None
        if payload.api_id:
            api = db.scalar(select(API).where(API.id == payload.api_id, API.org_id == org_id))
            if not api:
                raise ValueError("API not found")
        else:
            if not payload.api_name or not payload.base_url:
                raise ValueError("Either api_id or both api_name and base_url are required")
            api = db.scalar(select(API).where(API.org_id == org_id, API.name == payload.api_name))
            if not api:
                if not PlanService.check_api_quota(db, org_id=org_id, plan=plan):
                    raise PermissionError("Plan API quota exceeded")
                api = API(org_id=org_id, name=payload.api_name, base_url=str(payload.base_url))
                db.add(api)
                db.flush()
                api_created = True

        spec = OpenAPISpec(org_id=org_id, api_id=api.id, version=payload.version, raw_spec=payload.raw_spec)
        db.add(spec)

        endpoints_synced = 0
        paths = payload.raw_spec.get("paths") if isinstance(payload.raw_spec, dict) else None
        if isinstance(paths, dict):
            valid_methods = {"get", "post", "put", "patch", "delete", "head", "options"}
            for path, operations in paths.items():
                if not isinstance(path, str) or not isinstance(operations, dict):
                    continue
                for method in operations.keys():
                    if not isinstance(method, str) or method.lower() not in valid_methods:
                        continue
                    normalized_method = method.upper()
                    exists = db.scalar(
                        select(Endpoint).where(
                            Endpoint.api_id == api.id,
                            Endpoint.org_id == org_id,
                            Endpoint.path == path,
                            Endpoint.method == normalized_method,
                        )
                    )
                    if exists:
                        continue
                    endpoint = Endpoint(api_id=api.id, org_id=org_id, path=path, method=normalized_method)
                    db.add(endpoint)
                    endpoints_synced += 1

        db.commit()
        db.refresh(spec)
        db.refresh(api)
        return spec, api, api_created, endpoints_synced

    @staticmethod
    def upload_openapi_spec(db: Session, org_id: uuid.UUID, api_id: uuid.UUID, payload: OpenAPISpecCreate) -> OpenAPISpec:
        api = db.scalar(select(API).where(API.id == api_id, API.org_id == org_id))
        if not api:
            raise ValueError("API not found")
        spec = OpenAPISpec(org_id=org_id, api_id=api_id, version=payload.version, raw_spec=payload.raw_spec)
        db.add(spec)
        db.commit()
        db.refresh(spec)
        return spec

    @staticmethod
    def create_contract(db: Session, org_id: uuid.UUID, endpoint_id: uuid.UUID, payload: ContractCreate) -> Contract:
        endpoint = db.scalar(select(Endpoint).where(Endpoint.id == endpoint_id, Endpoint.org_id == org_id))
        if not endpoint:
            raise ValueError("Endpoint not found")
        contract = Contract(org_id=org_id, endpoint_id=endpoint_id, schema_hash=payload.schema_hash)
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract

    @staticmethod
    def list_specs(db: Session, org_id: uuid.UUID, api_id: uuid.UUID) -> list[OpenAPISpec]:
        return list(
            db.scalars(select(OpenAPISpec).where(OpenAPISpec.org_id == org_id, OpenAPISpec.api_id == api_id).order_by(OpenAPISpec.uploaded_at.desc())).all()
        )

    @staticmethod
    def enqueue_job(db: Session, org_id: uuid.UUID, job_type: str, payload: dict) -> Job:
        job = Job(org_id=org_id, type=job_type, payload=payload, status="pending", attempts=0, run_at=datetime.now(UTC))
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def claim_next_job(db: Session, org_id: uuid.UUID) -> Job | None:
        stmt = text(
            """
            SELECT id FROM jobs
            WHERE org_id = :org_id AND status = 'pending' AND run_at <= now()
            ORDER BY run_at ASC
            FOR UPDATE SKIP LOCKED
            LIMIT 1
            """
        )
        row = db.execute(stmt, {"org_id": str(org_id)}).first()
        if not row:
            return None
        job = db.get(Job, row[0])
        if not job:
            return None
        job.status = "running"
        job.attempts += 1
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def mark_job_failed_with_backoff(db: Session, job: Job, max_attempts: int = 5) -> Job:
        if job.attempts >= max_attempts:
            job.status = "failed"
        else:
            job.status = "pending"
            delay_seconds = 2 ** job.attempts
            job.run_at = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def mark_job_completed(db: Session, job: Job) -> Job:
        job.status = "completed"
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def hash_schema(raw_schema: dict) -> str:
        raw = str(raw_schema).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()
