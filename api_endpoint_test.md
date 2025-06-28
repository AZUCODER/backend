# API Endpoint Testing Guide

This document provides comprehensive curl commands to test all API endpoints. Update this file whenever new endpoints are added.

## Environment Setup

```bash
# Base URL
export BASE_URL="http://127.0.0.1:8000"
export API_BASE="$BASE_URL/api/v1"

# Test credentials (update as needed)
export TEST_EMAIL="test@example.com"
export TEST_USERNAME="testuser"
export TEST_PASSWORD="SecurePass123!"

# Token storage (will be populated after login)
export ACCESS_TOKEN=""
export REFRESH_TOKEN=""
```

## Root Endpoints

### 1. Root Information
```bash
curl -X GET "$BASE_URL/" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "message": "Welcome to FastAPI Backend",
  "version": "0.1.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

### 2. Health Check
```bash
curl -X GET "$BASE_URL/health" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

## API v1 Root

### 3. API Information
```bash
curl -X GET "$API_BASE/" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "message": "FastAPI Backend API v1",
  "version": "1.0.0",
  "endpoints": {
    "auth": "Authentication endpoints",
    "users": "User management endpoints (coming soon)"
  }
}
```

## Authentication Endpoints

### 4. User Registration
```bash
curl -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$TEST_EMAIL'",
    "username": "'$TEST_USERNAME'",
    "password": "'$TEST_PASSWORD'",
    "first_name": "Test",
    "last_name": "User",
    "full_name": "Test User"
  }'
```

**Expected Response (Success):**
```json
{
  "message": "User registered successfully",
  "success": true,
  "data": {
    "user_id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_verified": false
  }
}
```

**Expected Response (Error - Email exists):**
```json
{
  "detail": "Email already registered"
}
```

### 5. User Login
```bash
curl -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email_or_username": "'$TEST_EMAIL'",
    "password": "'$TEST_PASSWORD'"
  }'
```

**Expected Response (Success):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "is_verified": false,
    "is_active": true
  }
}
```

**Save tokens for subsequent requests:**
```bash
# After successful login, extract and save tokens
export ACCESS_TOKEN="your_access_token_here"
export REFRESH_TOKEN="your_refresh_token_here"
```

### 6. Refresh Token
```bash
curl -X POST "$API_BASE/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "'$REFRESH_TOKEN'"
  }'
```

**Expected Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### 7. Get Current User Profile
```bash
curl -X GET "$API_BASE/auth/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "first_name": "Test",
  "last_name": "User",
  "full_name": "Test User",
  "is_verified": false,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### 8. Get User Sessions
```bash
curl -X GET "$API_BASE/auth/sessions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "sessions": [
    {
      "id": 1,
      "user_agent": "curl/7.68.0",
      "ip_address": "127.0.0.1",
      "device_info": null,
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "last_used_at": "2024-01-15T10:35:00Z",
      "expires_at": "2024-01-22T10:30:00Z"
    }
  ],
  "total_sessions": 1,
  "active_sessions": 1
}
```

### 9. Revoke Specific Session
```bash
# Replace {session_id} with actual session ID
curl -X DELETE "$API_BASE/auth/sessions/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**Expected Response:**
```json
{
  "message": "Session revoked successfully",
  "success": true
}
```

### 10. User Logout
```bash
# Logout from current session only
curl -X POST "$API_BASE/auth/logout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "revoke_all": false
  }'

# Logout from all sessions
curl -X POST "$API_BASE/auth/logout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "revoke_all": true
  }'
```

**Expected Response:**
```json
{
  "message": "Logged out successfully",
  "success": true
}
```

## User Management Endpoints (Coming Soon)

### 11. List Users (Admin)
```bash
curl -X GET "$API_BASE/users/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -G \
  -d "page=1" \
  -d "size=20"
```

### 12. Get User by ID
```bash
# Replace {user_id} with actual user ID
curl -X GET "$API_BASE/users/1" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 13. Update User Profile
```bash
curl -X PUT "$API_BASE/users/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "first_name": "Updated",
    "last_name": "Name",
    "full_name": "Updated Name"
  }'
```

### 14. Change Password
```bash
curl -X POST "$API_BASE/users/change-password" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "current_password": "'$TEST_PASSWORD'",
    "new_password": "NewSecurePass123!"
  }'
```

### 15. Delete User Account
```bash
curl -X DELETE "$API_BASE/users/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "password": "'$TEST_PASSWORD'"
  }'
```

## Interactive Documentation

### Swagger UI
Open in browser: `http://127.0.0.1:8000/docs`

### ReDoc
Open in browser: `http://127.0.0.1:8000/redoc`

## Error Handling Examples

### 401 Unauthorized (Invalid/Expired Token)
```bash
curl -X GET "$API_BASE/auth/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid_token"
```

**Response:**
```json
{
  "detail": "Could not validate credentials"
}
```

### 400 Bad Request (Invalid Data)
```bash
curl -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "invalid-email",
    "username": "ab",
    "password": "weak"
  }'
```

**Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    },
    {
      "loc": ["body", "username"],
      "msg": "ensure this value has at least 3 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

### 422 Validation Error (Missing Fields)
```bash
curl -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response:**
```json
{
  "detail": [
    {
      "loc": ["body", "email_or_username"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "password"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Testing Workflow

### Complete Registration and Login Flow
```bash
#!/bin/bash

# 1. Register new user
echo "1. Registering user..."
curl -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$TEST_EMAIL'",
    "username": "'$TEST_USERNAME'",
    "password": "'$TEST_PASSWORD'",
    "first_name": "Test",
    "last_name": "User"
  }'

echo -e "\n\n2. Logging in..."
# 2. Login and extract tokens
RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email_or_username": "'$TEST_EMAIL'",
    "password": "'$TEST_PASSWORD'"
  }')

echo $RESPONSE

# Extract tokens (requires jq)
export ACCESS_TOKEN=$(echo $RESPONSE | jq -r '.access_token')
export REFRESH_TOKEN=$(echo $RESPONSE | jq -r '.refresh_token')

echo -e "\n\n3. Getting user profile..."
# 3. Get user profile
curl -X GET "$API_BASE/auth/me" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

echo -e "\n\n4. Getting user sessions..."
# 4. Get sessions
curl -X GET "$API_BASE/auth/sessions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

echo -e "\n\n5. Logging out..."
# 5. Logout
curl -X POST "$API_BASE/auth/logout" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"revoke_all": false}'
```

## Notes

- Replace environment variables with actual values
- Save tokens after login for authenticated requests
- Check server logs for detailed error information
- Use `jq` tool for JSON parsing in bash scripts
- Test error cases to ensure proper validation
- Update this file when new endpoints are added

## Common Issues

1. **CORS Error**: Ensure frontend origin is in `BACKEND_CORS_ORIGINS`
2. **Token Expired**: Use refresh token or login again
3. **Database Connection**: Check database URL in `.env`
4. **Port Conflict**: Ensure port 8000 is available 