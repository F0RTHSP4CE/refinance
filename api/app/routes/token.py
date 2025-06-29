"""API routes for Token manipulation"""

from app.schemas.token import TokenRequestSchema, TokenSendReportSchema
from app.services.token import TokenService
from app.services.entity import EntityService
from app.config import get_config
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth

token_router = APIRouter(prefix="/tokens", tags=["Tokens"])

oauth = OAuth()
config = get_config()
if config.oidc_client_id and config.oidc_client_secret and config.oidc_discovery_url:
    oauth.register(
        name="oidc",
        client_id=config.oidc_client_id,
        client_secret=config.oidc_client_secret,
        server_metadata_url=config.oidc_discovery_url,
        client_kwargs={"scope": "openid email profile"},
    )


@token_router.post("/request", response_model=TokenSendReportSchema)
def generate_and_send_new_token(
    token_request_schema: TokenRequestSchema,
    token_service: TokenService = Depends(),
):
    return token_service.generate_and_send_new_token(
        entity_id=token_request_schema.entity_id,
        entity_name=token_request_schema.entity_name,
        entity_telegram_id=token_request_schema.entity_telegram_id,
    )


@token_router.get("/oidc/login")
def oidc_login(request: Request):
    if not oauth.oidc:
        raise HTTPException(status_code=500, detail="OIDC not configured")
    redirect_uri = config.oidc_redirect_uri or str(request.url_for("oidc_callback"))
    return oauth.oidc.authorize_redirect(request, redirect_uri)


@token_router.get(
    "/oidc/callback",
)
async def oidc_callback(
    request: Request,
    response: Response,
    token_service: TokenService = Depends(),
    entity_service: EntityService = Depends(),
):
    if not oauth.oidc:
        raise HTTPException(status_code=500, detail="OIDC not configured")
    token = await oauth.oidc.authorize_access_token(request)
    userinfo = await oauth.oidc.parse_id_token(request, token)
    # Find or create entity by email or sub
    email = userinfo.get("email")
    sub = userinfo.get("sub")
    name = userinfo.get("name") or email or sub
    entity = None
    if email:
        try:
            entity = entity_service.get_by_name(email)
        except Exception:
            pass
    if not entity:
        # Create new entity if not found
        entity = entity_service.create(
            {"name": name, "auth": {"oidc_sub": sub, "email": email}}
        )
    # Issue JWT
    jwt_token = token_service._generate_new_token(entity.id)
    # Return token in a redirect (could also set cookie)
    redirect_url = f"{config.ui_url}/auth/token/{jwt_token}"
    return RedirectResponse(url=redirect_url)
