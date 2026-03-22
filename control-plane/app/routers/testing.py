import time

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.testing import TestRequest, TestResponse
from app.services.contract_service import ContractService

router = APIRouter()

@router.post("/request", response_model=TestResponse)
async def proxy_test_request(payload: TestRequest, request: Request, db: Session = Depends(get_db)):
    headers = payload.headers or {}
    start_time = time.time()
    org_id = getattr(request.state, "org_id", None)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=payload.method,
                url=str(payload.url),
                headers=headers,
                json=payload.body if isinstance(payload.body, (dict, list)) else None,
                data=payload.body if isinstance(payload.body, str) else None,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            try:
                resp_body = response.json()
            except ValueError:
                resp_body = response.text

            contract_validation = {
                "status": "missing",
                "endpoint_id": None,
                "path": str(payload.url.path),
                "method": payload.method.upper(),
                "contract_hash": None,
                "observed_hash": None,
            }
            if org_id:
                contract_validation = ContractService.validate_runtime_response(
                    db=db,
                    org_id=org_id,
                    method=payload.method,
                    request_url_or_path=str(payload.url),
                    response_body=resp_body,
                )
                
            return TestResponse(
                status=response.status_code,
                time_ms=elapsed_ms,
                size_bytes=len(response.content),
                body=resp_body,
                headers=dict(response.headers),
                contract_validation=contract_validation,
            )
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Proxy error: {str(exc)}")
