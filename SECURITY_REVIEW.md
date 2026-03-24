# Security Review - ELIOS

## Scope
- Backend FastAPI app (`backend/server.py`)
- Frontend React app (`frontend/src`)
- Deployment baseline (`docker-compose.yml`, Dockerfiles)

## High Priority Findings

1. **Hardcoded default JWT secret fallback**
   - Risk: token forgery if app runs with default secret.
   - Location: `backend/server.py` (`default-secret-key`).
   - Recommendation: fail startup if `JWT_SECRET` is missing in non-dev environments.

2. **Admin bootstrap endpoint returns static credentials**
   - Risk: account takeover if endpoint is exposed and not disabled after initialization.
   - Location: `POST /api/init/admin` in `backend/server.py`.
   - Recommendation: disable endpoint in production or require one-time setup token.

3. **Wildcard CORS allowed by default**
   - Risk: wider attack surface for browser-based requests.
   - Location: CORS middleware defaults to `*`.
   - Recommendation: set explicit allowed origins per environment.

4. **AI error details exposed to end users**
   - Risk: information leakage.
   - Location: AI exception messages returned directly in responses.
   - Recommendation: return generic user-safe errors and log detailed internals only server-side.

## Medium Priority Findings

1. **No brute-force protection on login endpoint**
   - Recommendation: add rate limiting and lockout policy.

2. **No password complexity check on change-password/register**
   - Recommendation: enforce minimum length and complexity rules.

3. **No explicit request size limits**
   - Recommendation: constrain payload size, especially in chat endpoints.

## Positive Notes
- Passwords are hashed with bcrypt.
- JWT expiration is configured.
- Role checks exist for admin routes.

## Immediate Action Plan
1. Configure `JWT_SECRET`, `CORS_ORIGINS`, and `AI_PROVIDER` only via env.
2. Rotate credentials and API keys already shared in chat.
3. Restrict `/init/*` endpoints to local setup workflow.
4. Add rate limiting middleware and standardized error handling.
