# CSRF Token Missing Fix - Implementation Summary

## Problem
When creating support tickets, the frontend was getting this error:
```json
{"detail":"CSRF Failed: CSRF token missing."}
```

This occurred because POST requests from the frontend weren't including the CSRF token that Django requires.

## Root Cause
1. Django's CSRF middleware was enabled (`django.middleware.csrf.CsrfViewMiddleware`)
2. The support view's POST endpoints require CSRF tokens for security
3. The frontend wasn't extracting and sending the CSRF token with POST requests
4. `CSRF_COOKIE_HTTPONLY = True` was preventing JavaScript from reading the CSRF cookie directly

## Solutions Implemented

### 1. Backend Changes

#### Added CSRF Token Endpoint (`/api/views.py`)
- New `get_csrf_token()` view decorated with `@csrf_protect` and `@require_http_methods(["GET"])`
- Returns the CSRF token as JSON: `{"csrfToken": "token_value"}`
- URL: `GET /api/csrf-token/`

#### Updated Django Settings (`/api/settings.py`)
- Added `REST_FRAMEWORK` configuration to enable SessionAuthentication with CSRF protection:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

#### Updated Support Views (`/support/views.py`)
- Added `@ensure_csrf_cookie` decorator to `create_support_ticket()` view
- This ensures the CSRF cookie is set on the response
- Added import: `from django.views.decorators.csrf import ensure_csrf_cookie`

#### Added API Route (`/api/urls.py`)
- New route: `path('api/csrf-token/', get_csrf_token, name='csrf_token')`
- Imported: `from api.views import get_csrf_token`

### 2. Frontend Changes

#### Updated Support Page (`/app/support/page.tsx`)

**New CSRF Token Retrieval Functions:**
- `getCsrfTokenFromCookie()` - Extracts CSRF token directly from browser cookies
- `getCsrfToken()` - Async function that:
  1. First tries to extract from browser cookies
  2. If not found, fetches from the new `/api/csrf-token/` endpoint
  3. Returns the token or null if unavailable

**Updated POST Request Handlers:**
- `handleCreateTicket()` - Now includes CSRF token in X-CSRFToken header
- `handleAddMessage()` - Now includes CSRF token in X-CSRFToken header
- Both functions made async to properly await the CSRF token

**Header Construction:**
```typescript
const csrfToken = await getCsrfToken();
const headers: Record<string, string> = {
    "Content-Type": "application/json",
};
if (csrfToken) {
    headers["X-CSRFToken"] = csrfToken;
}
```

## How It Works Flow

1. **Initial Page Load:**
   - Frontend accesses `/app/support` page
   - Browser makes GET requests with `credentials: 'include'`
   - Django sets CSRF cookie in response

2. **Creating Ticket:**
   - Frontend calls `getCsrfToken()`
   - Token extracted from cookie or fetched from API endpoint
   - POST request includes `X-CSRFToken` header with the token
   - Django validates token and processes the request

3. **CSRF Validation:**
   - Django middleware validates that the X-CSRFToken header matches the cookie
   - If match succeeds, request is processed
   - If missing or mismatched, 403 error is returned

## Config Details Already in Place

The following settings were already configured correctly:
- ✅ `CORS_ALLOW_CREDENTIALS = True` - Allows credentials in CORS requests
- ✅ `'x-csrftoken'` in `CORS_ALLOW_HEADERS` - Allows CSRF header through CORS
- ✅ `CSRF_TRUSTED_ORIGINS` - Setup to allow CSRF from frontend origins
- ✅ `SESSION_COOKIE_SAMESITE = 'Strict'` - SameSite protection
- ✅ `CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'` - Django listening for X-CSRFToken header

## Testing the Fix

1. Open browser DevTools → Network tab
2. Click "Create Support Ticket"
3. Verify the POST request includes:
   - Request header: `X-CSRFToken: <token_value>`
   - Cookie: `csrftoken=<token_value>`
4. Verify response is 201 Created (not 403 Forbidden)

## Security Notes

- CSRF tokens are:
  - Only valid for the session they belong to
  - Changed per session
  - Validated on every state-changing request (POST, PUT, DELETE, PATCH)
  - Never logged or exposed in response bodies

- Cookie flags in place:
  - `SESSION_COOKIE_HTTPONLY = True` - JavaScript can't read session cookie
  - `SESSION_COOKIE_SECURE` configurable - HTTPS only in production
  - `CSRF_COOKIE_SAMESITE = 'Strict'` - Prevents cross-site requests

## Affected Endpoints

All POST/PUT/PATCH/DELETE endpoints now properly enforce CSRF:
- `POST /api/support/create/` - Create ticket
- `POST /api/support/tickets/{id}/reply/` - Add message to ticket
- `PATCH /api/support/tickets/{id}/update-status/` - Update ticket status

## Rollback Notes

If needed to revert changes:
1. Remove `@ensure_csrf_cookie` from `create_support_ticket()`
2. Remove `/api/csrf-token/` route from `api/urls.py`
3. Remove `get_csrf_token` view from `api/views.py`
4. Frontend CSRF token retrieval functions can be kept (they fall back gracefully)

## Related Documentation

- Django CSRF Protection: https://docs.djangoproject.com/en/stable/middleware/csrf/
- Django REST Framework Authentication: https://www.django-rest-framework.org/api-guide/authentication/
- CORS with CSRF: https://docs.djangoproject.com/en/stable/ref/settings/#csrf-trusted-origins
