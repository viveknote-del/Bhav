from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth import verify_token

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    return verify_token(credentials.credentials)


def require_user(user: dict = Depends(get_current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
