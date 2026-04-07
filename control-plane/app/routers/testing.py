import ipaddress
import socket
import time
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.testing import TestRequest, TestResponse
from app.services.contract_service import ContractService

router = APIRouter()


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_outbound_test_url(raw_url: str) -> None:
    parsed = urlsplit(raw_url)
    scheme = (parsed.scheme or "").lower()
    host = (parsed.hostname or "").strip().lower()
    port = parsed.port or (443 if scheme == "https" else 80)

    if scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="Only http/https URLs are allowed")
    if not host:
        raise HTTPException(status_code=400, detail="Invalid target URL")
    if host == "localhost":
        raise HTTPException(status_code=400, detail="Local/internal targets are not allowed")

    try:
        ip = ipaddress.ip_address(host)
        if _is_blocked_ip(ip):
            raise HTTPException(status_code=400, detail="Private/internal targets are not allowed")
        return
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Target host cannot be resolved")

    for info in infos:
        resolved = ipaddress.ip_address(info[4][0])
        if _is_blocked_ip(resolved):
            raise HTTPException(status_code=400, detail="Target resolves to private/internal IP")

@router.post("/request", response_model=TestResponse)
async def proxy_test_request(payload: TestRequest, request: Request, db: Session = Depends(get_db)):
    headers = payload.headers or {}
    start_time = time.time()
    org_id = getattr(request.state, "org_id", None)
    target_url = str(payload.url)
    _validate_outbound_test_url(target_url)
    
    async with httpx.AsyncClient(follow_redirects=False, timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        try:
            response = await client.request(
                method=payload.method,
                url=target_url,
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
