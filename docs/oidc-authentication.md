# OIDC Authentication

Refinance now supports OIDC (OpenID Connect) authentication alongside existing Telegram-based authentication. This allows users to log in via any OIDC-compliant provider such as Authelia, Keycloak, Auth0, Google, etc.

## Configuration

Add the following environment variables to configure OIDC:

```bash
# OIDC Provider Configuration
REFINANCE_OIDC_CLIENT_ID=your-client-id
REFINANCE_OIDC_CLIENT_SECRET=your-client-secret
REFINANCE_OIDC_SERVER_METADATA_URL=https://your-provider.com/.well-known/openid_configuration
REFINANCE_OIDC_REDIRECT_URI=https://your-api-domain.com/auth/oidc/callback
```

### Configuration Details

- `REFINANCE_OIDC_CLIENT_ID`: OAuth2 client ID provided by your OIDC provider
- `REFINANCE_OIDC_CLIENT_SECRET`: OAuth2 client secret provided by your OIDC provider  
- `REFINANCE_OIDC_SERVER_METADATA_URL`: OIDC discovery endpoint URL (usually ends with `/.well-known/openid_configuration`)
- `REFINANCE_OIDC_REDIRECT_URI`: Callback URL that your OIDC provider should redirect to after authentication (must match your API's `/auth/oidc/callback` endpoint)

### Example: Authelia Configuration

For Authelia, your configuration might look like:

```bash
REFINANCE_OIDC_CLIENT_ID=refinance
REFINANCE_OIDC_CLIENT_SECRET=your-secret-here
REFINANCE_OIDC_SERVER_METADATA_URL=https://auth.yourdomain.com/.well-known/openid_configuration
REFINANCE_OIDC_REDIRECT_URI=https://api.yourdomain.com/auth/oidc/callback
```

And in your Authelia configuration:

```yaml
identity_providers:
  oidc:
    clients:
      - id: refinance
        description: Refinance Finance App
        secret: your-secret-here
        public: false
        authorization_policy: one_factor
        redirect_uris:
          - https://api.yourdomain.com/auth/oidc/callback
        scopes:
          - openid
          - email
          - profile
```

## Usage

### Login Flow

1. Direct users to `/auth/oidc/login` to initiate OIDC authentication
2. Users will be redirected to your OIDC provider for authentication
3. After successful authentication, users are redirected back to `/auth/oidc/callback`
4. The system will create or map the user to a local Entity and issue a JWT token
5. Users are redirected to the UI with the JWT token

### User Mapping

The OIDC service maps OIDC users to local Entities using the following logic:

1. **Existing OIDC User**: If an Entity already exists with the same `oidc_subject`, use that Entity
2. **Existing Email User**: If an Entity exists with the same email address, map it to the OIDC subject
3. **New User**: Create a new Entity with OIDC information

### Entity Structure

Entities with OIDC authentication will have an `auth` field like:

```json
{
  "auth": {
    "oidc_subject": "unique-subject-from-provider",
    "email": "user@example.com"
  }
}
```

Entities can support multiple authentication methods simultaneously:

```json
{
  "auth": {
    "oidc_subject": "unique-subject-from-provider", 
    "email": "user@example.com",
    "telegram_id": 123456789
  }
}
```

## Security

- OIDC flows use standard OAuth2/OIDC security practices
- State parameters are used for CSRF protection
- JWT tokens issued after OIDC authentication use the same security model as Telegram authentication
- All existing endpoint security and `get_entity_from_token` middleware remain unchanged

## Compatibility

- Telegram authentication continues to work exactly as before
- Existing JWT tokens remain valid
- All existing API endpoints work with OIDC-authenticated users
- No changes required to client applications using the API

## API Endpoints

- `GET /auth/oidc/login` - Initiate OIDC authentication
- `GET /auth/oidc/callback` - Handle OIDC provider callback

Optional query parameters for `/auth/oidc/login`:
- `redirect_url` - Custom URL to redirect to after authentication (defaults to UI token handler)