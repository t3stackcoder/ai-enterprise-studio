# Auth Server Fix Documentation

## Problem
The Auth Server was failing to start with the error:
```
AttributeError: 'PGDialect_psycopg2' object has no attribute 'UUID'
```

## Root Causes

### 1. Missing PostgreSQL Adapter
- `psycopg2-binary` was not listed in `requirements.txt`
- SQLAlchemy couldn't properly connect to PostgreSQL

### 2. Incorrect UUID Type Implementation
- The custom UUID type in `libs/models/user.py` was trying to use `dialect.UUID()`
- This attribute doesn't exist in the psycopg2 dialect
- Needed to import UUID type explicitly from `sqlalchemy.dialects.postgresql`

## Fixes Applied

### 1. Updated `libs/models/user.py`
**Changed:**
```python
from sqlalchemy.dialects.postgresql import UUID as PostgreSQL_UUID

def load_dialect_impl(self, dialect):
    if dialect.name == "postgresql":
        return dialect.type_descriptor(PostgreSQL_UUID(as_uuid=True))
    else:
        return dialect.type_descriptor(SQLString(36))
```

**Why:** Properly imports and uses the PostgreSQL UUID type instead of trying to access it from the dialect object.

### 2. Updated `apps/auth-server/requirements.txt`
**Added:**
```
psycopg2-binary>=2.9.9  # PostgreSQL adapter
```

**Why:** SQLAlchemy needs psycopg2 to communicate with PostgreSQL databases.

### 3. Updated `start.bat`
**Added:**
```batch
REM Start PostgreSQL database
echo Starting PostgreSQL database...
docker-compose up -d postgres
echo Waiting for database to be ready...
timeout /t 10 /nobreak >nul
```

**Why:** Auth Server requires PostgreSQL to be running before it can start.

## Installation

To apply these fixes:

1. **Install the missing dependency:**
   ```bash
   cd apps\auth-server
   pip install psycopg2-binary
   ```

2. **Start the services:**
   ```bash
   .\start.bat
   ```

## Testing

Test the Auth Server manually:
```bash
.\test-auth.bat
```

Or test individual components:
```bash
# 1. Start database
docker-compose up -d postgres

# 2. Start auth server
cd apps\auth-server
python server.py
```

## Expected Output

When successful, you should see:
```
2025-10-18 16:54:17,769 - server - INFO - 🚀 Starting Auth Server...
Database initialized: postgresql://ai_studio:***@localhost:5432/ai_studio_db
2025-10-18 16:54:17,769 - server - INFO - ✅ Auth Server ready!
2025-10-18 16:54:17,769 - server - INFO - 📚 API Docs: http://localhost:8000/api/docs
INFO:     Application startup complete.
```

## Services Overview

After running `start.bat`, the following services will be available:
- **PostgreSQL**: localhost:5432
- **Auth Server**: http://localhost:8001
- **Analysis Server**: ws://localhost:8765
- **Web Analysis**: http://localhost:3001
- **Web Shell**: http://localhost:3000
