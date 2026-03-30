# API Contract (Frontend)

Base URL: /api

This document defines the request/response contract for the current API.

## Core Standards (Important)

- Use numeric IDs for primary/foreign keys (PK/FK) in requests and responses.
- Use real values for content fields (e.g., title, description, email).
- Send JSON bodies for POST requests.
- Do not send extra fields not listed per endpoint.

## Auth Endpoints

### POST /api/register/

Request body:
{
  "username": "string",
  "email": "string",
  "password": "string",
  "role": "string"  // role lookup key: INST, STUD, ADMIN
}

Response (201):
{
  "message": "User registered successfully.",
  "tokens": {
    "refresh": "string",
    "access": "string"
  }
}

### POST /api/login/

Request body:
{
  "username": "string",
  "password": "string"
}

Response (200):
{
  "message": "Login successful.",
  "tokens": {
    "refresh": "string",
    "access": "string"
  }
}

### POST /api/token/

Request body:
{
  "username": "string",
  "password": "string"
}

Response (200, also sets HttpOnly cookies):
{
  "refresh": "string",
  "access": "string"
}

### POST /api/token/refresh/

Request body:
{
  "refresh": "string"  // optional if refresh cookie exists
}

Response (200, also updates HttpOnly cookies):
{
  "access": "string",
  "refresh": "string"  // present when refresh rotation is enabled
}

### POST /api/logout/

Request body: {}

Response (200):
{
  "message": "Logged out."
}

## Course Endpoints

### GET /api/courses/

Request body: none

Auth: required (cookie or Authorization header)

Behavior:
- If role is STUD: returns enrolled courses
- If role is INST: returns courses taught by user
- If role is ADMIN or unauthenticated: empty list

Response (200):
[
  {
    "id": 1,
    "title": "string",
    "description": "string",
    "created_at": "string",
    "updated_at": "string",
    "instructor": {
      "id": 10,
      "username": "string",
      "email": "string"
    },
    "enrolled_students": [
      {
        "id": 20,
        "username": "string",
        "email": "string"
      }
    ]
  }
]

### POST /api/courses/

Request body:
{
  "title": "string",
  "description": "string"
}

Auth: required (must be INST role)

Response (201):
{
  "id": 1,
  "title": "string",
  "description": "string",
  "created_at": "string",
  "updated_at": "string",
  "instructor": {
    "id": 10,
    "username": "string",
    "email": "string"
  }
}

### DELETE /api/courses/<course_id>/

Request body: none

Auth: required (must be INST role and instructor of the course)

Response (204):
No content

## Authentication Usage (Frontend)

Option A: Cookie-based auth (recommended)
- Call /api/token/ on login to set cookies
- Browser sends cookies automatically
- Use /api/token/refresh/ to refresh access token
- Use /api/logout/ to clear cookies

Option B: Authorization header
- Send: Authorization: Bearer <access_token>
- Use refresh token to get a new access token when expired
