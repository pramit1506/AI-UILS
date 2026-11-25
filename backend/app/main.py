import secrets
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.security import AUTH_COOKIE_NAME, CSRF_COOKIE_NAME, CSRF_HEADER_NAME
from app.api.v1.api import api_router
from app.exceptions.base import BaseApplicationException
from app.exceptions.handlers import (
    application_exception_handler,
    validation_exception_handler,
    global_exception_handler,
)
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.logging import LoggingMiddleware

CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
CSRF_FAIL_DETAIL = "CSRF check failed"


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Double-submit CSRF protection for cookie-authenticated browser requests.

    Applies ONLY to state-changing methods (POST/PUT/PATCH/DELETE) under the
    API prefix, and ONLY when the request is cookie-authenticated — i.e. no
    Bearer header AND an `uils_access` cookie is present. In that case the
    `x-csrf-token` header must equal the `uils_csrf` cookie (constant-time
    compare). Requests using Bearer auth, or with no access cookie at all
    (unauthenticated endpoints like login/register), are exempt.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method.upper()
        if (
            method in CSRF_PROTECTED_METHODS
            and request.url.path.startswith(settings.API_V1_STR)
            and "authorization" not in request.headers
            and request.cookies.get(AUTH_COOKIE_NAME)
        ):
            header_token = request.headers.get(CSRF_HEADER_NAME)
            cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
            if (
                not header_token
                or not cookie_token
                or not secrets.compare_digest(header_token, cookie_token)
            ):
                return JSONResponse(status_code=403, content={"detail": CSRF_FAIL_DETAIL})
        return await call_next(request)


from app.database.init_db import init_database

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    _validate_security_config()
    if settings.AUTH_COOKIE_SECURE is False:
        logger.info("Session cookies permit HTTP. Use this configuration only on a local loopback listener.")
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    await init_database()
    from app.services.password_recovery import is_configured
    if not is_configured():
        logger.warning("Password recovery email is disabled. Configure a sender and SMTP or Mailjet.")
    yield
    # Release resources created over the app's lifetime: LLM provider clients
    # (previously recreated per request without cleanup) and the persistent
    # checkpointer's SQLite connection.
    logger.info(f"Shutting down {settings.PROJECT_NAME}...")
    from app.llm.factory import shutdown_llm_clients
    from app.dependencies.graph import shutdown_graph
    try:
        await shutdown_llm_clients()
    except Exception as exc:
        logger.warning(f"LLM client shutdown skipped: {exc}")
    try:
        await shutdown_graph()
    except Exception as exc:
        logger.warning(f"Graph/checkpointer shutdown skipped: {exc}")


# Secrets that are committed to source control — using any of these in a
# deployed (DEBUG=False) environment would let anyone mint valid JWTs.
_INSECURE_DEFAULT_SECRETS = {
    "uils_jwt_default_secret_key_change_in_production_min32bytes",
    "change-me",
    "your-secret-key-min-32-chars-long",
    "",
}


def _validate_security_config() -> None:
    if settings.SECRET_KEY in _INSECURE_DEFAULT_SECRETS:
        if not settings.DEBUG:
            # Fail fast: with a publicly-known signing key an attacker can forge
            # tokens for any user id and take over arbitrary accounts.
            raise RuntimeError(
                "SECRET_KEY is an insecure default but DEBUG=False. "
                "Set a strong, unique SECRET_KEY (>= 32 random characters) in the environment."
            )
        logger.warning(
            "SECRET_KEY is an insecure default. Tokens are forgeable in local/dev mode; "
            "set a strong SECRET_KEY before any deployment."
        )
    elif len(settings.SECRET_KEY) < 32:
        logger.warning("SECRET_KEY is shorter than 32 characters; consider a longer key.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.API_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
        debug=settings.DEBUG,
    )

    # CORS configuration
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*", CSRF_HEADER_NAME],
        )

    # CSRF double-submit protection (cookie-auth only; Bearer requests exempt).
    # Registered right after CORS so 403 responses still carry CORS headers.
    app.add_middleware(CSRFMiddleware)

    # Custom Middlewares
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)

    # Exception Handlers
    app.add_exception_handler(BaseApplicationException, application_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)

    return app

app = create_app()
