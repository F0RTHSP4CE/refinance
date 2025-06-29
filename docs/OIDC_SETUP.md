# OIDC Authentication Setup Guide

This guide explains how to set up OpenID Connect (OIDC) authentication for the refinance application.

## Prerequisites

- An OIDC provider (Google, Microsoft, Auth0, etc.)
- Client credentials from your OIDC provider
- The refinance application running with API accessible

## Configuration

### 1. OIDC Provider Setup

#### Google OAuth 2.0
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set authorized redirect URIs to: `http://your-domain:8000/auth/oidc/callback`

#### Microsoft Azure AD
1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to "Azure Active Directory" → "App registrations"
3. Create a new registration
4. Set redirect URI to: `http://your-domain:8000/auth/oidc/callback`

#### Auth0
1. Go to [Auth0 Dashboard](https://manage.auth0.com/)
2. Create a new application (type: Regular Web Application)
3. Set allowed callback URLs to: `http://your-domain:8000/auth/oidc/callback`

### 2. Environment Variables

Add the following to your `secrets.env` file:

```bash
# Required OIDC Configuration
export REFINANCE_OIDC_CLIENT_ID=your-client-id
export REFINANCE_OIDC_CLIENT_SECRET=your-client-secret
export REFINANCE_OIDC_DISCOVERY_URL=https://your-provider/.well-known/openid_configuration

# Optional - defaults to "openid profile email"
export REFINANCE_OIDC_SCOPES=openid profile email
```

### 3. Discovery URLs by Provider

| Provider | Discovery URL |
|----------|---------------|
| Google | `https://accounts.google.com/.well-known/openid_configuration` |
| Microsoft | `https://login.microsoftonline.com/common/v2.0/.well-known/openid_configuration` |
| Auth0 | `https://your-domain.auth0.com/.well-known/openid_configuration` |

## Account Linking

### Initial Setup
When OIDC is first configured, existing users will need to link their OIDC accounts:

1. **For new users**: They can log in directly with OIDC
2. **For existing users**: An administrator needs to manually link accounts

### Manual Account Linking (Admin)

To link an OIDC account to an existing entity, update the entity's `auth` field:

```python
# Example: Link Google account to entity
entity = session.query(Entity).filter_by(name="john_doe").first()
if entity.auth is None:
    entity.auth = {}
entity.auth['oidc_sub'] = 'google-oauth2|123456789'  # From OIDC userinfo
entity.auth['oidc_email'] = 'john@example.com'       # From OIDC userinfo
session.commit()
```

### Automatic Linking by Email

The system will automatically link OIDC accounts to existing entities if:
1. The OIDC account has an email
2. An entity already exists with that email in their `oidc_email` field
3. The OIDC subject (`sub`) is not already linked to another entity

## Security Considerations

1. **HTTPS in Production**: Always use HTTPS in production
2. **Secure Cookies**: The implementation uses HttpOnly cookies for session data
3. **State Validation**: CSRF protection via state parameter validation
4. **PKCE**: Uses Proof Key for Code Exchange for additional security
5. **Token Validation**: Proper validation of OIDC tokens and userinfo

## Troubleshooting

### Common Issues

1. **"OIDC not configured" error**
   - Check that all required environment variables are set
   - Verify the discovery URL is accessible

2. **"Invalid authorization code" error**
   - Check redirect URI matches exactly what's configured in OIDC provider
   - Verify client ID and secret are correct

3. **"No entity found for this OIDC account" error**
   - The user needs to be linked to an existing entity
   - Create a new entity or link to existing one as described above

4. **Session/state errors**
   - Clear browser cookies and try again
   - Check that cookies are enabled in the browser

### Debug Mode

For debugging, you can add logging to see the OIDC flow:

```python
import logging
logging.getLogger('app.services.oidc').setLevel(logging.DEBUG)
```

## API Endpoints

- `GET /auth/oidc/login` - Initiate OIDC login
- `GET /auth/oidc/callback` - Handle OIDC callback (web flow)
- `POST /auth/oidc/callback` - Handle OIDC callback (API flow)

## Integration with Existing Auth

OIDC authentication works alongside existing token-based authentication:

- Users can have both Telegram and OIDC authentication
- Each authentication method is stored in the entity's `auth` JSON field
- Users can log in with either method
- No migration is required for existing users