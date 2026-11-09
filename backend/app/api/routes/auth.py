from fastapi import APIRouter, Request, Response

from app.api.deps import CurrentUser, SessionDep
from app.core.config import get_settings
from app.core.errors import Forbidden
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,  # not readable by JavaScript: an XSS bug cannot steal the session
        secure=settings.effective_cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
        path="/",
    )


def _client(request: Request) -> tuple[str | None, str | None]:
    return request.headers.get("user-agent"), request.client.host if request.client else None


@router.post("/register", response_model=UserOut, status_code=201, summary="Create an account and sign in")
async def register(payload: RegisterIn, request: Request, response: Response, session: SessionDep) -> UserOut:
    if not get_settings().allow_registration:
        raise Forbidden("Sign-up is disabled on this server.", code="registration_disabled")
    user, token = await auth_service.register(session, payload, user_agent=_client(request)[0], ip=_client(request)[1])
    _set_session_cookie(response, token)
    return auth_service.to_user_out(user)


@router.post("/login", response_model=UserOut, summary="Sign in (sets the httpOnly session cookie)")
async def login(payload: LoginIn, request: Request, response: Response, session: SessionDep) -> UserOut:
    user, token = await auth_service.login(session, payload, user_agent=_client(request)[0], ip=_client(request)[1])
    _set_session_cookie(response, token)
    return auth_service.to_user_out(user)


@router.post("/logout", status_code=204, summary="Sign out and revoke the session")
async def logout(request: Request, session: SessionDep) -> Response:
    settings = get_settings()
    await auth_service.logout(session, request.cookies.get(settings.session_cookie_name))
    response = Response(status_code=204)
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        domain=settings.cookie_domain,
        secure=settings.effective_cookie_secure,
        httponly=True,
        samesite=settings.cookie_samesite,
    )
    return response


@router.get("/me", response_model=UserOut, summary="The signed-in user (401 when signed out)")
async def me(user: CurrentUser) -> UserOut:
    return auth_service.to_user_out(user)
