"""OIDC (OpenID Connect) authentication endpoints"""

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth, OAuthError
from app.config import get_config
from app.services.token import TokenService
from app.services.entity import EntityService
from app.models.entity import Entity
from app.schemas.entity import EntityCreateSchema, EntityAuthSchema
from sqlalchemy.orm import Session
from app.uow import get_uow
import logging

router = APIRouter(prefix="/auth/oidc", tags=["OIDC"])

logger = logging.getLogger(__name__)


def get_oauth():
    config = get_config()
    oauth = OAuth()
    oauth.register(
        name="oidc",
        client_id=config.oidc_client_id,
        client_secret=config.oidc_client_secret,
        server_metadata_url=config.oidc_discovery_url,
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


@router.get("/login")
async def login(request: Request):
    oauth = get_oauth()
    config = get_config()
    redirect_uri = config.oidc_redirect_uri
    return await oauth.oidc.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(
    request: Request,
    db: Session = Depends(get_uow),
    entity_service: EntityService = Depends(),
    token_service: TokenService = Depends(),
):
    oauth = get_oauth()
    config = get_config()
    try:
        token = await oauth.oidc.authorize_access_token(request)
        userinfo = token.get("userinfo", {})
    except OAuthError as e:
        logger.error(f"OIDC error: {e}")
        return JSONResponse(
            status_code=400, content={"error": "OIDC authentication failed"}
        )

    # Find or create entity by email (or sub)
    entity = None
    if "email" in userinfo:
        print(f"Searching entity by email: {userinfo['email']}")
        try:
            entity = entity_service.get_by_oidc_email(userinfo["email"])
            print(f"Found entity by email: {entity}")
        except Exception:
            entity = None
    if not entity:
        # Create new entity if not found
        name = (
            userinfo.get("preferred_username")
            or userinfo.get("email")
            or userinfo.get("sub")
            or f"oidc-{userinfo.get('sub', '')}"
            or "oidc-user"
        )
        if not name:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "OIDC user info missing unique identifier for entity name"
                },
            )
        entity = entity_service.create(
            EntityCreateSchema(
                name=name,
                auth=EntityAuthSchema(
                    oidc_email=userinfo.get("email"),
                    oidc_sub=userinfo.get("sub")
                )
            )
        )

    # Issue internal token
    internal_token = token_service._generate_new_token(entity.id)

    # Redirect to UI with token (could also set cookie)
    ui_url = config.ui_url.rstrip("/")
    redirect_url = f"{ui_url}/auth/token/{internal_token}"
    return RedirectResponse(redirect_url, status_code=status.HTTP_302_FOUND)
