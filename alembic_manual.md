# Alembic Manual & Cheatsheet

## Overview
Alembic is a database migration tool for SQLAlchemy. This project uses Alembic with SQLModel and PostgreSQL for database schema management.

## Quick Reference

### Essential Commands

#### Initialize & Setup
```bash
# Initialize Alembic (already done)
alembic init alembic

# Check current status
alembic current

# Check migration history
alembic history
```

#### Creating Migrations
```bash
# Create a new migration (auto-generate from model changes)
alembic revision --autogenerate -m "Description of changes"

# Create empty migration for manual editing
alembic revision -m "Manual migration description"

# Create migration with specific revision ID
alembic revision --rev-id abc123 -m "Description"
```

#### Running Migrations
```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Downgrade to specific revision
alembic downgrade <revision_id>

# Downgrade one step
alembic downgrade -1

# Downgrade to base (remove all migrations)
alembic downgrade base
```

#### Migration Status & Info
```bash
# Show current migration status
alembic current

# Show migration history
alembic history

# Show detailed history
alembic history --verbose

# Show specific revision info
alembic show <revision_id>

# Check what would be migrated
alembic check
```

#### Stamping & Marking
```bash
# Mark database as being at specific revision (without running migrations)
alembic stamp <revision_id>

# Mark database as being at head
alembic stamp head
```

## Project-Specific Configuration

### Database URL
- **Development**: `postgresql+psycopg://postgres:postgres@localhost:5432/aixiate_db`
- **Production**: Set via environment variable `DATABASE_URL`

### Auto-Formatting
This project automatically formats migration files using:
- **Black**: Code formatting
- **Ruff**: Linting and auto-fix

### File Naming Convention
Migrations use timestamped filenames: `YYYY_MM_DD_HHMM-<revision>_<description>.py`

## Best Practices

### 1. Migration Naming
```bash
# Good examples
alembic revision --autogenerate -m "Add user table"
alembic revision --autogenerate -m "Add email verification fields"
alembic revision --autogenerate -m "Create session management tables"

# Bad examples
alembic revision --autogenerate -m "fix"
alembic revision --autogenerate -m "update"
```

### 2. Migration Workflow
1. **Make model changes** in `app/models/`
2. **Generate migration**: `alembic revision --autogenerate -m "Description"`
3. **Review generated migration** in `alembic/versions/`
4. **Test migration**: `alembic upgrade head`
5. **Commit changes** to version control

### 3. Before Committing
- Always review auto-generated migrations
- Test both upgrade and downgrade paths
- Ensure migration files are committed with model changes

## Common Scenarios

### Adding a New Model
```python
# 1. Add model to app/models/
class NewModel(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

# 2. Generate migration
alembic revision --autogenerate -m "Add new model table"

# 3. Apply migration
alembic upgrade head
```

### Modifying Existing Model
```python
# 1. Modify model in app/models/
class User(SQLModel, table=True):
    # ... existing fields ...
    new_field: Optional[str] = Field(default=None)  # Add this

# 2. Generate migration
alembic revision --autogenerate -m "Add new_field to user table"

# 3. Apply migration
alembic upgrade head
```

### Removing a Field
```python
# 1. Remove field from model
class User(SQLModel, table=True):
    # Remove: old_field: str
    # Keep other fields...

# 2. Generate migration
alembic revision --autogenerate -m "Remove old_field from user table"

# 3. Apply migration
alembic upgrade head
```

## Troubleshooting

### Common Issues

#### 1. "Target database is not up to date"
```bash
# Check current status
alembic current

# Apply pending migrations
alembic upgrade head
```

#### 2. "Can't locate revision identified by"
```bash
# Check available revisions
alembic history

# Stamp database to current state
alembic stamp head
```

#### 3. Migration conflicts
```bash
# Check migration history
alembic history --verbose

# If needed, create a merge migration
alembic merge -m "Merge heads" <revision1> <revision2>
```

#### 4. Database connection issues
```bash
# Check database URL in alembic.ini
# Ensure PostgreSQL is running
# Verify credentials and database exists
```

### Manual Migration Editing

Sometimes auto-generated migrations need manual adjustment:

```python
# Example: Manual migration file
"""Add user preferences

Revision ID: abc123def456
Revises: previous_revision
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers
revision = 'abc123def456'
down_revision = 'previous_revision'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add column with default value
    op.add_column('user', sa.Column('preferences', sa.JSON(), nullable=True))
    
    # Update existing rows
    op.execute("UPDATE user SET preferences = '{}' WHERE preferences IS NULL")
    
    # Make column not nullable
    op.alter_column('user', 'preferences', nullable=False)

def downgrade() -> None:
    op.drop_column('user', 'preferences')
```

## Environment-Specific Commands

### Development
```bash
# Standard workflow
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Production
```bash
# Always backup before migrations
pg_dump your_database > backup.sql

# Run migrations
alembic upgrade head

# Verify migration
alembic current
```

### Testing
```bash
# Create test database
createdb test_aixiate_db

# Set test database URL
export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/test_aixiate_db"

# Run migrations on test database
alembic upgrade head

# Test downgrade
alembic downgrade -1
```

## Useful Aliases

Add these to your shell profile for convenience:

```bash
# .bashrc or .zshrc
alias alembic-status="alembic current"
alias alembic-history="alembic history --verbose"
alias alembic-upgrade="alembic upgrade head"
alias alembic-downgrade="alembic downgrade -1"
alias alembic-generate="alembic revision --autogenerate -m"
```

## Database Seeding with Alembic

### Overview
Database seeding is the process of populating your database with initial data. Alembic provides several approaches for seeding data during migrations.

### Seeding Strategies

#### 1. Seed Data in Migration Files (Recommended for Initial Data)

Create a migration specifically for seeding:

```bash
# Create a seed migration
alembic revision -m "Seed initial data"
```

Example seed migration:

```python
"""Seed initial data

Revision ID: seed_initial_data
Revises: previous_migration
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime
import uuid

# revision identifiers
revision = 'seed_initial_data'
down_revision = 'previous_migration'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Get connection
    connection = op.get_bind()
    
    # Seed users table
    users_data = [
        {
            'id': 1,
            'email': 'admin@example.com',
            'username': 'admin',
            'hashed_password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.i8i.',  # 'password'
            'is_active': True,
            'is_verified': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'id': 2,
            'email': 'user@example.com',
            'username': 'user',
            'hashed_password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.i8i.',  # 'password'
            'is_active': True,
            'is_verified': True,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]
    
    # Insert users
    for user_data in users_data:
        connection.execute(
            sa.text("""
                INSERT INTO user (id, email, username, hashed_password, is_active, is_verified, created_at, updated_at)
                VALUES (:id, :email, :username, :hashed_password, :is_active, :is_verified, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """),
            user_data
        )

def downgrade() -> None:
    # Remove seeded data
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM user WHERE id IN (1, 2)"))
```

#### 2. Conditional Seeding (Only if Table is Empty)

```python
def upgrade() -> None:
    connection = op.get_bind()
    
    # Check if table is empty
    result = connection.execute(sa.text("SELECT COUNT(*) FROM user"))
    count = result.scalar()
    
    if count == 0:
        # Only seed if table is empty
        users_data = [
            {
                'email': 'admin@example.com',
                'username': 'admin',
                'hashed_password': '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.i8i.',
                'is_active': True,
                'is_verified': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        ]
        
        for user_data in users_data:
            connection.execute(
                sa.text("""
                    INSERT INTO user (email, username, hashed_password, is_active, is_verified, created_at, updated_at)
                    VALUES (:email, :username, :hashed_password, :is_active, :is_verified, :created_at, :updated_at)
                """),
                user_data
            )

def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM user WHERE email = 'admin@example.com'"))
```

#### 3. Using SQLModel in Migrations

For more complex seeding with your existing models:

```python
"""Seed with SQLModel

Revision ID: seed_with_sqlmodel
Revises: previous_migration
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlmodel import Session, create_engine
from app.models.user import User
from app.core.security import get_password_hash
from datetime import datetime

# revision identifiers
revision = 'seed_with_sqlmodel'
down_revision = 'previous_migration'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Get database URL from config
    from app.config import get_settings
    settings = get_settings()
    
    # Create engine
    engine = create_engine(settings.DATABASE_URL)
    
    with Session(engine) as session:
        # Check if admin user exists
        existing_admin = session.query(User).filter(User.email == "admin@example.com").first()
        
        if not existing_admin:
            # Create admin user
            admin_user = User(
                email="admin@example.com",
                username="admin",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_verified=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(admin_user)
            session.commit()

def downgrade() -> None:
    engine = create_engine(settings.DATABASE_URL)
    
    with Session(engine) as session:
        admin_user = session.query(User).filter(User.email == "admin@example.com").first()
        if admin_user:
            session.delete(admin_user)
            session.commit()
```

### Seeding Commands

#### Create Seed Migration
```bash
# Create a seed migration
alembic revision -m "Seed initial data"

# Create seed migration with specific ID
alembic revision --rev-id seed_data -m "Seed initial data"
```

#### Run Seed Migration
```bash
# Apply seed migration
alembic upgrade head

# Apply specific seed migration
alembic upgrade seed_data
```

#### Revert Seed Migration
```bash
# Downgrade seed migration
alembic downgrade -1

# Or downgrade to specific revision before seed
alembic downgrade previous_migration
```

### Best Practices for Seeding

#### 1. Use UUIDs for IDs (Implemented)
```python
import uuid

def upgrade() -> None:
    connection = op.get_bind()
    
    user_data = {
        'id': str(uuid.uuid4()),
        'email': 'admin@example.com',
        'username': 'admin',
        # ... other fields
    }
    
    connection.execute(
        sa.text("INSERT INTO users (id, email, username, ...) VALUES (:id, :email, :username, ...)"),
        user_data
    )
```

**Note**: This project now uses UUIDs for all primary keys and foreign keys. All models inherit from `BaseModel` which automatically generates UUIDs.

#### 2. Handle Conflicts Gracefully
```python
def upgrade() -> None:
    connection = op.get_bind()
    
    # Use ON CONFLICT for PostgreSQL
    connection.execute(
        sa.text("""
            INSERT INTO user (email, username, hashed_password, is_active, is_verified)
            VALUES (:email, :username, :hashed_password, :is_active, :is_verified)
            ON CONFLICT (email) DO NOTHING
        """),
        user_data
    )
```

#### 3. Seed Environment-Specific Data
```python
import os

def upgrade() -> None:
    connection = op.get_bind()
    environment = os.getenv("ENVIRONMENT", "development")
    
    if environment == "development":
        # Seed development data
        dev_users = [
            {'email': 'dev1@example.com', 'username': 'dev1'},
            {'email': 'dev2@example.com', 'username': 'dev2'},
        ]
        # ... insert dev data
    elif environment == "staging":
        # Seed staging data
        staging_users = [
            {'email': 'staging@example.com', 'username': 'staging'},
        ]
        # ... insert staging data
```

#### 4. Seed with Relationships
```python
def upgrade() -> None:
    connection = op.get_bind()
    
    # Insert parent record first
    connection.execute(
        sa.text("INSERT INTO user (id, email, username) VALUES (:id, :email, :username)"),
        {'id': 1, 'email': 'admin@example.com', 'username': 'admin'}
    )
    
    # Insert related records
    connection.execute(
        sa.text("INSERT INTO user_profile (user_id, bio) VALUES (:user_id, :bio)"),
        {'user_id': 1, 'bio': 'System Administrator'}
    )
```

### Seeding Scripts (Alternative Approach)

Create standalone seeding scripts outside of Alembic:

```python
# scripts/seed_database.py
import asyncio
from sqlmodel import Session, create_engine
from app.models.user import User
from app.core.security import get_password_hash
from app.config import get_settings

async def seed_database():
    settings = get_settings()
    engine = create_engine(settings.DATABASE_URL)
    
    with Session(engine) as session:
        # Check if data exists
        existing_user = session.query(User).filter(User.email == "admin@example.com").first()
        
        if not existing_user:
            admin_user = User(
                email="admin@example.com",
                username="admin",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_verified=True
            )
            session.add(admin_user)
            session.commit()
            print("Database seeded successfully!")
        else:
            print("Database already contains seed data.")

if __name__ == "__main__":
    asyncio.run(seed_database())
```

Run the script:
```bash
# Run seeding script
python scripts/seed_database.py

# Or integrate with FastAPI startup
```

### Integration with FastAPI

#### Startup Seeding
```python
# In your FastAPI app startup
from alembic import command
from alembic.config import Config
import os

def run_startup_migrations_and_seed():
    alembic_cfg = Config("alembic.ini")
    
    # Run migrations
    command.upgrade(alembic_cfg, "head")
    
    # Run seeding if in development
    if os.getenv("ENVIRONMENT") == "development":
        # Run seed migration or script
        pass
```

#### Seeding Endpoint (Development Only)
```python
@app.post("/admin/seed-database")
async def seed_database():
    if os.getenv("ENVIRONMENT") != "development":
        raise HTTPException(status_code=403, detail="Seeding only allowed in development")
    
    # Run seeding logic
    # ... seeding code ...
    
    return {"message": "Database seeded successfully"}
```

## Integration with FastAPI

### Startup Migration Check
```python
# In your FastAPI app startup
from alembic import command
from alembic.config import Config

def run_startup_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
```

### Health Check Endpoint
```python
from alembic import command
from alembic.config import Config

@app.get("/health/db-migrations")
async def check_migrations():
    try:
        alembic_cfg = Config("alembic.ini")
        command.check(alembic_cfg)
        return {"status": "migrations_up_to_date"}
    except Exception as e:
        return {"status": "migrations_pending", "error": str(e)}
```

## Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Project Structure

```
backend/
├── alembic/
│   ├── env.py              # Alembic environment configuration
│   ├── script.py.mako      # Migration template
│   └── versions/           # Migration files
├── alembic.ini            # Alembic configuration
├── app/
│   └── models/            # SQLModel definitions
└── alembic_manual.md      # This file
```
