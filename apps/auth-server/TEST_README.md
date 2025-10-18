# Auth Server Tests

Comprehensive test suite for the authentication server, covering signup, signin, token refresh, and RBAC functionality.

## Test Structure

```
auth-server/
├── conftest.py           # Pytest configuration and fixtures
├── test_auth.py          # Authentication tests (signup, signin, refresh)
├── test_rbac.py          # Role-based access control tests
└── pyproject.toml        # Pytest configuration
```

## Test Database

Tests use an **in-memory SQLite database** for fast, isolated testing:
- Session-scoped database engine (created once, shared across all tests)
- Session-scoped table creation (auth module creates/drops its tables)
- Function-scoped sessions with automatic truncation after each test

## Prerequisites

1. Install dependencies:
```powershell
cd apps/auth-server
pip install -r requirements.txt
```

2. Ensure `.env` file exists in project root with test configuration

## Running Tests

### Run all tests
```powershell
pytest
```

### Run specific test file
```powershell
pytest test_auth.py
pytest test_rbac.py
```

### Run specific test class
```powershell
pytest test_auth.py::TestUserRegistration
pytest test_rbac.py::TestUserRoles
```

### Run specific test
```powershell
pytest test_auth.py::TestUserRegistration::test_register_new_user_success
```

### Run with verbose output
```powershell
pytest -v
```

### Run with output from print statements
```powershell
pytest -s
```

### Run tests matching a keyword
```powershell
pytest -k "login"
pytest -k "refresh"
pytest -k "rbac"
```

### Run tests by marker
```powershell
pytest -m auth
pytest -m rbac
```

### Run with coverage report
```powershell
pytest --cov=. --cov-report=html
```

## Test Categories

### Authentication Tests (`test_auth.py`)

#### User Registration
- ✅ Successful user registration
- ✅ Duplicate username rejection
- ✅ Duplicate email rejection
- ✅ Missing required fields validation
- ✅ Invalid email format validation

#### User Login
- ✅ Successful login with valid credentials
- ✅ Invalid username rejection
- ✅ Invalid password rejection
- ✅ Last login timestamp update
- ✅ Missing credentials validation

#### Access Token
- ✅ Token contains correct user information
- ✅ Token expiration time is correct
- ✅ Protected endpoints work with valid token
- ✅ Protected endpoints reject requests without token
- ✅ Protected endpoints reject invalid tokens

#### Refresh Token
- ✅ Refresh token generation and storage
- ✅ Successful token refresh
- ✅ Invalid refresh token rejection
- ✅ Invalid user_id rejection
- ✅ Expired refresh token rejection
- ✅ New access token works on protected endpoints

### RBAC Tests (`test_rbac.py`)

#### User Roles
- ✅ User role in access token
- ✅ Admin role in access token
- ✅ Enterprise role in access token
- ✅ Multiple users with different roles

#### Subscription Tiers
- ✅ Free tier users
- ✅ Enterprise tier users
- ✅ New users default to free tier

#### RBAC Scenarios
- ✅ Users can access their own profile
- ✅ Admin can access their own profile
- ✅ Enterprise can access their own profile
- ✅ Token refresh preserves role
- ✅ Token refresh preserves subscription tier
- ✅ Different users have isolated sessions
- ✅ Role information in profile endpoint

#### Security Scenarios
- ✅ Cannot use another user's refresh token
- ✅ Token contains unique user identifier
- ✅ Password never returned in profile
- ✅ Registration doesn't return sensitive data

## Test Fixtures

### Database Fixtures
- `test_engine` - Session-scoped in-memory SQLite engine
- `TestSessionLocal` - Session factory
- `setup_auth_tables` - Creates/drops auth tables (auto-use)
- `db_session` - Function-scoped DB session with auto-truncate

### User Fixtures
- `sample_user` - Regular user (role: user, tier: free)
- `admin_user` - Admin user (role: admin, tier: enterprise)
- `enterprise_user` - Enterprise user (role: enterprise, tier: enterprise)

### Authenticated Client Fixtures
- `authenticated_client` - Client with logged-in regular user
- `authenticated_admin_client` - Client with logged-in admin
- `authenticated_enterprise_client` - Client with logged-in enterprise user

## Environment Variables

Test configuration is loaded from `.env` file:

```env
# Test Database
TEST_DATABASE_URL=sqlite:///:memory:

# Test User Credentials
TEST_USER_USERNAME=testuser
TEST_USER_PASSWORD=password123
TEST_USER_EMAIL=test@example.com

TEST_ADMIN_USERNAME=adminuser
TEST_ADMIN_PASSWORD=admin123
TEST_ADMIN_EMAIL=admin@example.com

TEST_ENTERPRISE_USERNAME=enterpriseuser
TEST_ENTERPRISE_PASSWORD=enterprise123
TEST_ENTERPRISE_EMAIL=enterprise@example.com

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

## Test Isolation

Each test is completely isolated:
1. Tables are created once at session start
2. Each test gets a fresh database session
3. All data is automatically truncated after each test
4. No test can affect another test's data

## Troubleshooting

### Import Errors
Make sure you're in the `auth-server` directory and `libs` is in the Python path.

### Database Errors
Tests use in-memory SQLite, so no database setup is needed. If you see errors, ensure `sqlalchemy` is installed.

### Test Failures
- Check that `.env` file exists with correct test configuration
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Run with `-v` flag for more detailed output: `pytest -v`

## Adding New Tests

1. Add test to appropriate file (`test_auth.py` or `test_rbac.py`)
2. Use descriptive test names starting with `test_`
3. Group related tests in classes starting with `Test`
4. Use existing fixtures from `conftest.py`
5. Document what the test validates

Example:
```python
class TestNewFeature:
    """Test new authentication feature"""
    
    def test_feature_works(self, client, sample_user):
        """Test that new feature works as expected"""
        response = client.post("/auth/new-endpoint", json={...})
        assert response.status_code == 200
```
