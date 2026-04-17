"""Service for managing API contracts and OpenAPI specifications."""
import hashlib
import json
from urllib.parse import urlparse
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.api import API
from app.models.contract import Contract
from app.models.endpoint import Endpoint
from app.models.openapi_spec import OpenAPISpec
from app.schemas.api import ContractCreate, OpenAPIUploadRequest, OpenAPISpecCreate
from app.services.plan_service import PlanService


class ContractService:
    """Service for contract creation, validation, and OpenAPI management."""
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
    def hash_schema(raw_schema: dict) -> str:
        raw = json.dumps(raw_schema, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def _extract_response_schema(operation: dict) -> dict | None:
        responses = operation.get("responses")
        if not isinstance(responses, dict):
            return None

        ordered_codes: list[str] = []
        for code in ("200", "201", "202", "default"):
            if code in responses:
                ordered_codes.append(code)
        for code in responses.keys():
            if code not in ordered_codes:
                ordered_codes.append(code)

        for code in ordered_codes:
            response = responses.get(code)
            if not isinstance(response, dict):
                continue
            content = response.get("content")
            if not isinstance(content, dict) or not content:
                continue

            media = content.get("application/json")
            if not isinstance(media, dict):
                media = next((v for v in content.values() if isinstance(v, dict)), None)
            if not isinstance(media, dict):
                continue

            schema = media.get("schema")
            if isinstance(schema, dict):
                return schema
        return None

    @staticmethod
    def sync_contracts_from_openapi(
        db: Session,
        org_id: uuid.UUID,
        api_id: uuid.UUID,
        spec_id: uuid.UUID,
    ) -> int:
        spec = db.scalar(
            select(OpenAPISpec).where(
                OpenAPISpec.id == spec_id,
                OpenAPISpec.org_id == org_id,
                OpenAPISpec.api_id == api_id,
            )
        )
        if not spec:
            raise ValueError("OpenAPI spec not found")

        endpoints = list(
            db.scalars(
                select(Endpoint).where(
                    Endpoint.org_id == org_id,
                    Endpoint.api_id == api_id,
                )
            ).all()
        )
        endpoint_map = {(endpoint.path, endpoint.method): endpoint for endpoint in endpoints}

        valid_methods = {"get", "post", "put", "patch", "delete", "head", "options"}
        paths = spec.raw_spec.get("paths") if isinstance(spec.raw_spec, dict) else None
        if not isinstance(paths, dict):
            return 0

        synced_count = 0
        for path, operations in paths.items():
            if not isinstance(path, str) or not isinstance(operations, dict):
                continue
            for method, operation in operations.items():
                if not isinstance(method, str) or method.lower() not in valid_methods or not isinstance(operation, dict):
                    continue

                endpoint = endpoint_map.get((path, method.upper()))
                if not endpoint:
                    continue

                schema = ContractService._extract_response_schema(operation)
                if not schema:
                    continue

                schema_hash = ContractService.hash_schema(schema)
                contract = db.scalar(
                    select(Contract).where(
                        Contract.org_id == org_id,
                        Contract.endpoint_id == endpoint.id,
                    )
                )
                if contract:
                    contract.schema_hash = schema_hash
                    db.add(contract)
                else:
                    db.add(
                        Contract(
                            org_id=org_id,
                            endpoint_id=endpoint.id,
                            schema_hash=schema_hash,
                        )
                    )
                synced_count += 1

        db.commit()
        return synced_count

    @staticmethod
    def _normalize_path(path: str) -> str:
        if not path:
            return "/"
        parsed = urlparse(path)
        resolved = parsed.path if parsed.scheme or parsed.netloc else path
        if not resolved.startswith("/"):
            resolved = f"/{resolved}"
        return resolved.rstrip("/") or "/"

    @staticmethod
    def _path_matches(template_path: str, actual_path: str) -> bool:
        left = ContractService._normalize_path(template_path).split("/")
        right = ContractService._normalize_path(actual_path).split("/")
        if len(left) != len(right):
            return False
        for expected, current in zip(left, right, strict=True):
            if expected.startswith("{") and expected.endswith("}"):
                continue
            if expected != current:
                return False
        return True

    @staticmethod
    def _infer_runtime_schema(value):
        if value is None:
            return {"type": "null"}
        if isinstance(value, bool):
            return {"type": "boolean"}
        if isinstance(value, int):
            return {"type": "integer"}
        if isinstance(value, float):
            return {"type": "number"}
        if isinstance(value, str):
            return {"type": "string"}
        if isinstance(value, dict):
            keys = sorted(value.keys())
            return {
                "type": "object",
                "required": keys,
                "properties": {key: ContractService._infer_runtime_schema(value[key]) for key in keys},
            }
        if isinstance(value, list):
            if len(value) == 0:
                return {"type": "array", "items": {"type": "null"}}
            item_schemas = [ContractService._infer_runtime_schema(item) for item in value]
            unique_items: list[dict] = []
            seen: set[str] = set()
            for schema in item_schemas:
                marker = json.dumps(schema, sort_keys=True, separators=(",", ":"))
                if marker in seen:
                    continue
                seen.add(marker)
                unique_items.append(schema)
            if len(unique_items) == 1:
                items_schema = unique_items[0]
            else:
                items_schema = {"anyOf": unique_items}
            return {"type": "array", "items": items_schema}
        return {"type": "string"}

    @staticmethod
    def validate_runtime_response(
        db: Session,
        org_id: uuid.UUID,
        method: str,
        request_url_or_path: str,
        response_body,
    ) -> dict:
        normalized_method = method.upper()
        request_path = ContractService._normalize_path(request_url_or_path)

        candidates = list(
            db.scalars(
                select(Endpoint).where(
                    Endpoint.org_id == org_id,
                    Endpoint.method == normalized_method,
                )
            ).all()
        )
        endpoint = next(
            (candidate for candidate in candidates if ContractService._path_matches(candidate.path, request_path)),
            None,
        )
        if not endpoint:
            return {
                "status": "missing",
                "endpoint_id": None,
                "path": request_path,
                "method": normalized_method,
                "contract_hash": None,
                "observed_hash": None,
            }

        contract = db.scalar(
            select(Contract)
            .where(
                Contract.org_id == org_id,
                Contract.endpoint_id == endpoint.id,
            )
            .order_by(Contract.created_at.desc())
        )
        if not contract:
            return {
                "status": "missing",
                "endpoint_id": endpoint.id,
                "path": endpoint.path,
                "method": endpoint.method,
                "contract_hash": None,
                "observed_hash": None,
            }

        observed_schema = ContractService._infer_runtime_schema(response_body)
        observed_hash = ContractService.hash_schema(observed_schema)
        return {
            "status": "valid" if observed_hash == contract.schema_hash else "warning",
            "endpoint_id": endpoint.id,
            "path": endpoint.path,
            "method": endpoint.method,
            "contract_hash": contract.schema_hash,
            "observed_hash": observed_hash,
        }
