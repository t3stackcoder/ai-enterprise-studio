# Auth Server

FastAPI-based authentication and authorization service for AI Enterprise Studio.

## Features

- ✅ **JWT Authentication** - Access and refresh tokens
- ✅ **User Registration & Login** - Email/password authentication
- ✅ **Role-Based Access Control (RBAC)** - Admin, Premium, User roles
- ✅ **Password Hashing** - Secure bcrypt hashing
- ✅ **SQLAlchemy ORM** - Support for PostgreSQL and SQLite
- ✅ **FastAPI** - Modern, fast API framework
- ✅ **Modular Architecture** - Extension-method style setup

## Quick Start

### 1. Install Dependencies

```bash
cd apps/auth-server
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

**Important**: Change the `JWT_SECRET_KEY` in production!

### 3. Run the Server

```bash
python server.py
```

Server will start on `http://localhost:8000`

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## API Endpoints

### Public Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get tokens
- `POST /api/auth/refresh` - Refresh access token

### Protected Endpoints

- `GET /api/user/profile` - Get current user profile (requires auth)
- `GET /api/admin/users` - Admin only endpoint
- `POST /api/premium/ai-analysis` - Premium/Admin only

### Testing

- `GET /health` - Health check
- `PUT /api/test/update-user-role` - Update user role for testing

## Example Usage

### Register a User

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123",
    "email_address": "test@example.com",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "abc123...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### Access Protected Endpoint

```bash
curl -X GET http://localhost:8000/api/user/profile \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Database

### SQLite (Development)

Default configuration uses SQLite. Database file: `auth_server.db`

### PostgreSQL (Production)

Update `.env`:

```env
DATABASE_URL=postgresql://username:password@localhost:5432/auth_db
```

### Migrations (Optional)

To set up Alembic for database migrations:

```bash
alembic init alembic
# Edit alembic.ini and alembic/env.py
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Architecture

The server uses a modular "extension method" pattern:

```python
from auth_setup import setup_auth_core, setup_auth_rbac

app = FastAPI()

setup_auth_core(app)      # JWT, CORS, login/register
setup_auth_rbac(app)      # Role-based endpoints
```

### Files

- `server.py` - Main application entry point
- `database.py` - SQLAlchemy session management
- `auth_service.py` - Authentication business logic
- `auth_endpoints.py` - FastAPI route handlers
- `auth_dependencies.py` - JWT verification, RBAC dependencies
- `auth_setup.py` - Extension methods for setup

## Security

- Passwords are hashed with bcrypt
- JWTs are signed with HS256
- Token expiration: 24 hours (access), 30 days (refresh)
- CORS configured for specific origins

**Production Checklist:**
- [ ] Change `JWT_SECRET_KEY` (min 32 characters)
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set `reload=False` in uvicorn
- [ ] Configure HTTPS/TLS
- [ ] Set up proper CORS origins
- [ ] Enable rate limiting
- [ ] Add monitoring/logging

## Integration

This auth server can be integrated with:
- Frontend apps (web-shell, web-analysis)
- Other backend services (analysis-server)
- API Gateway
- Microservices architecture

Example frontend integration:

```typescript
// Login
const response = await fetch('http://localhost:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'test', password: 'password123' })
});

const { access_token } = await response.json();

// Use token in requests
const profile = await fetch('http://localhost:8000/api/user/profile', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
```

## License

Part of AI Enterprise Studio
