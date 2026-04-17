from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Query

from ..services.user_store import user_store


router = APIRouter()


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _require_current_user(authorization: Optional[str]) -> Dict[str, Any]:
    token = _extract_bearer_token(authorization)
    if token is None:
        raise HTTPException(status_code=401, detail="authorization required")
    user = user_store.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return user


def _issue_auth_response(user: Dict[str, Any]) -> Dict[str, Any]:
    token = user_store.create_auth_token(user["id"])
    return {"token": token, "user": user}


@router.post("/register")
async def register(payload: Dict[str, Any]):
    try:
        user = user_store.register_user(
            name=(payload.get("name") or "").strip(),
            email=(payload.get("email") or "").strip(),
            password=payload.get("password") or "",
            department=(payload.get("department") or "").strip() or None,
            role=payload.get("role"),
            avatar=payload.get("avatar"),
            company_code=(payload.get("company_code") or "").strip() or None,
            company_name=(payload.get("company_name") or "").strip() or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _issue_auth_response(user)


@router.post("/login")
async def login(payload: Dict[str, Any]):
    user = user_store.authenticate_user(
        email=(payload.get("email") or "").strip(),
        password=payload.get("password") or "",
    )
    if user is None:
        raise HTTPException(status_code=401, detail="invalid email or password")
    return _issue_auth_response(user)


@router.get("/me")
async def me(authorization: Optional[str] = Header(default=None)):
    return _require_current_user(authorization)


@router.get("/company-members")
async def list_company_members(
    authorization: Optional[str] = Header(default=None),
    q: Optional[str] = Query(default=None),
):
    current_user = _require_current_user(authorization)
    return {
        "users": user_store.list_company_members(current_user.get("company_id"), query=q)
    }


@router.get("/users")
async def list_users(
    authorization: Optional[str] = Header(default=None),
    q: Optional[str] = Query(default=None),
):
    current_user = _require_current_user(authorization)
    return {
        "users": user_store.list_company_members(current_user.get("company_id"), query=q)
    }
