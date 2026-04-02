# omagent/server/auth.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from omagent.core.config import get_config

security = HTTPBearer(auto_error=False)


async def verify_bearer_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> None:
    """Verify bearer token if OMAGENT_API_KEY is configured.

    If no API key is set, auth is disabled (dev mode).
    /health endpoint is always exempt.
    """
    config = get_config()

    # No API key configured = dev mode, skip auth
    if not config.api_key:
        return

    # /health is always public
    if request.url.path == "/health":
        return

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail={"error": "Missing authorization header", "hint": "Use 'Authorization: Bearer <your-api-key>'"},
        )

    if credentials.credentials != config.api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": "Invalid API key"},
        )
