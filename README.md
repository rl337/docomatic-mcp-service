# Doc-O-Matic

A structured, agent-friendly documentation system designed to serve as the single source of truth for specifications, feature docs, implementation notes, and interface descriptions. Documents are hierarchical and Markdown-based. Agents retrieve, update, and write to sections — but Doc-O-Matic is not a note-taking app or a wiki.

Doc-O-Matic is designed to be used with MCP (Model Context Protocol), allowing AI agents to seamlessly interact with the documentation system through standardized MCP tools and functions.

## What Doc-O-Matic Is

✅ **A structured document store for specs and implementation docs**

Each document has:
- A title and unique ID
- Nested sections, each with its own heading, body, and metadata
- Documents and sections can be linked to:
  - Tasks in [To-Do-Rama](https://github.com/rl337/todorama)
  - Facts in [Bucket-O-Facts](https://github.com/rl337/bucketofacts)
  - Commits or files in GitHub

## What Doc-O-Matic Is Not

❌ A wiki or free-form note system  
❌ A changelog, blog, or publishing platform  
❌ A repo for unstructured content

## Features

### In Scope

- Create/edit structured Markdown documents with hierarchical sections
- Attach metadata per section (last modified, source task, related facts)
- Retrieve sections by topic, heading, or linked fact/task
- Export documents to GitHub as .md files
- MCP integration for agent-friendly interactions

### Not in Scope

- File uploads, diagrams, or image handling
- Document styling or rich presentation
- Arbitrary content blobs or external embeds
- Real-time collaboration or inline comments

## Installation

### Prerequisites

- **Python 3.10+** (Python 3.11+ recommended)
- **UV** (for dependency management) - [Install UV](https://github.com/astral-sh/uv#installation)
- **PostgreSQL** (for production) or **SQLite** (for development/testing)
- **Git** (for GitHub integration)

**Note**: UV is the standard dependency manager for all MCP services (TODO service, Bucket-O-Facts, Doc-O-Matic) for consistency and performance.

### Install Dependencies

#### Using UV (Recommended)

```bash
# Clone the repository
git clone https://github.com/rl337/docomatic-mcp-service.git
cd docomatic-mcp-service

# Install dependencies
uv sync

# Activate virtual environment (optional)
source .venv/bin/activate

# Or use uv run for commands (no activation needed)
uv run python -m docomatic.mcp_server
```

#### Using pip (Alternative)

```bash
# Clone the repository
git clone https://github.com/rl337/docomatic-mcp-service.git
cd docomatic-mcp-service

# Install in development mode
pip install -e .

# Or install with all dependencies
pip install -e ".[dev]"
```

## Running with Docker

Doc-O-Matic can be run in Docker containers using `docker-compose`, following the same patterns as the [TODO service](https://github.com/rl337/todorama) and [Bucket-O-Facts](https://github.com/rl337/bucket-o-facts).

### Prerequisites

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)

### Quick Start

1. **Set up environment variables**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env with your values (at minimum, change POSTGRES_PASSWORD)
   # See .env.example for all available options
   ```

2. **Start services**:
   ```bash
   # Start PostgreSQL and Doc-O-Matic services
   docker compose up -d
   
   # Verify services are running
   docker compose ps
   ```

3. **Run database migrations**:
   ```bash
   # Run migrations in the container
   docker compose exec doc-o-matic uv run alembic upgrade head
   ```

4. **Verify the service**:
   ```bash
   # Check service logs
   docker compose logs doc-o-matic
   
   # The MCP server should be running and ready for stdio communication
   ```

### Detailed Steps

#### 1. Environment Configuration

The `.env.example` file provides a template with all required and optional environment variables:

```bash
# Required for containerized setup
POSTGRES_DB=docomatic
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres  # ⚠️ Change this in production!

# Database connection (automatically configured for docker-compose)
DATABASE_URL=postgresql://postgres:postgres@postgresql:5432/docomatic

# Optional: GitHub token for export functionality
GITHUB_TOKEN=ghp_your_token_here
```

**Important**: Change `POSTGRES_PASSWORD` from the default value in production environments.

#### 2. External Network Integration

Doc-O-Matic creates a Docker network (`docomatic-mcp-service_doc-o-matic-network`) that can be used by other services for cross-container communication. This enables services in different Docker Compose projects to communicate.

**Network Name**: `docomatic-mcp-service_doc-o-matic-network`  
**Pattern**: `{project-name}_{network-name}`

**Other services can connect to this network** by declaring it as an external network in their `docker-compose.yml`:

```yaml
networks:
  doc-o-matic-network:
    external: true
    name: docomatic-mcp-service_doc-o-matic-network
```

Then reference it in their services:

```yaml
services:
  my-service:
    networks:
      - doc-o-matic-network
```

**Benefits:**
- ✅ Services can communicate using container names (e.g., `http://doc-o-matic:8005`)
- ✅ Network persists even if Doc-O-Matic stops (if other services reference it)
- ✅ Enables independent deployment and scaling of services
- ✅ No need for a single monolithic docker-compose file

**Note**: The network is created automatically when Doc-O-Matic starts. Other services must start after Doc-O-Matic to ensure the network exists.

#### 3. Building the Docker Image

```bash
# Build the image
docker build -t doc-o-matic .

# Verify the image was created
docker images | grep doc-o-matic
```

#### 3. Starting Services

```bash
# Start all services (PostgreSQL + Doc-O-Matic)
docker compose up -d

# View logs
docker compose logs -f doc-o-matic

# Check service status
docker compose ps
```

#### 4. Database Migrations

After starting the services, run database migrations:

```bash
# Run migrations
docker compose exec doc-o-matic uv run alembic upgrade head

# Verify schema was created (optional)
docker compose exec postgresql psql -U postgres -d docomatic -c "\dt"
```

#### 5. Accessing the MCP Server

Doc-O-Matic exposes an **HTTP SSE endpoint** at `/mcp/sse` for MCP client integration:

- **Health Check**: Verify the service is running:
  ```bash
  curl http://localhost:8005/health
  ```

- **MCP SSE Endpoint**: Access the MCP server via HTTP:
  ```bash
  curl http://localhost:8005/mcp/sse
  ```

- **Via MCP clients**: Configure your MCP client (e.g., Cursor) to use:
  ```
  http://localhost:8005/mcp/sse
  ```

**Note**: The service runs as an HTTP SSE server on port 8005 (configurable via `DOCOMATIC_SERVICE_PORT`).

#### 6. Stopping and Cleanup

```bash
# Stop services (keeps data)
docker compose down

# Stop and remove volumes (⚠️ deletes all data)
docker compose down -v

# View logs before stopping
docker compose logs doc-o-matic
```

### Differences from Local Development

When running in Docker:

- **Database**: Uses PostgreSQL (not SQLite) - configured automatically via docker-compose
- **Environment Variables**: Loaded from `.env` file (not shell environment)
- **Data Persistence**: Uses Docker volumes (`postgres_data` and `doc_o_matic_data`)
- **Isolation**: Service runs in isolated container with its own network

### Troubleshooting

#### Service won't start

```bash
# Check logs for errors
docker compose logs doc-o-matic

# Verify PostgreSQL is healthy
docker compose ps postgresql

# Check if port conflicts exist (unlikely for stdio-based service)
docker compose ps
```

#### Database connection errors

```bash
# Verify PostgreSQL is running and healthy
docker compose ps postgresql

# Check PostgreSQL logs
docker compose logs postgresql

# Test database connection from Doc-O-Matic container
docker compose exec doc-o-matic python -c "
from docomatic.storage.database import Database
db = Database()
print('Database connection:', 'OK' if db else 'FAILED')
"
```

#### Migration errors

```bash
# Check migration status
docker compose exec doc-o-matic uv run alembic current

# View migration history
docker compose exec doc-o-matic uv run alembic history

# If needed, rollback and re-run
docker compose exec doc-o-matic uv run alembic downgrade -1
docker compose exec doc-o-matic uv run alembic upgrade head
```

#### Viewing logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs doc-o-matic
docker compose logs postgresql

# Follow logs in real-time
docker compose logs -f doc-o-matic

# Last 100 lines
docker compose logs --tail=100 doc-o-matic
```

#### Resetting the environment

```bash
# Stop and remove containers and volumes (⚠️ deletes all data)
docker compose down -v

# Rebuild and restart
docker compose build
docker compose up -d
docker compose exec doc-o-matic uv run alembic upgrade head
```

#### Service appears to hang

Since Doc-O-Matic is stdio-based, it may appear "idle" when not receiving input. This is normal behavior. The service is waiting for MCP protocol messages via stdin.

### Production Considerations

For production deployments:

1. **Change default passwords**: Update `POSTGRES_PASSWORD` in `.env`
2. **Use secrets management**: Consider using Docker secrets or external secret managers
3. **Resource limits**: Adjust CPU and memory limits in `docker-compose.yml` based on workload
4. **Backup strategy**: Implement regular backups of the `postgres_data` volume
5. **Monitoring**: Set up logging and monitoring for container health
6. **Network security**: Use Docker networks and firewall rules to restrict access

### Reference

- Similar containerization patterns: [TODO service](https://github.com/rl337/todorama), [Bucket-O-Facts](https://github.com/rl337/bucket-o-facts)
- MCP Services Containerization Standards: [CONTAINERIZATION.md](../agenticness/CONTAINERIZATION.md)

## Setup

### 1. Database Configuration

Doc-O-Matic supports both PostgreSQL (production) and SQLite (development/testing).

#### SQLite (Development/Testing - Default)

No additional setup required. SQLite database will be created automatically at `./docomatic.db`.

```bash
# SQLite is used by default
# No configuration needed
```

#### PostgreSQL (Production)

1. **Install PostgreSQL** (if not already installed):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS (using Homebrew)
   brew install postgresql
   ```

2. **Create database**:
   ```bash
   createdb docomatic
   ```

3. **Set environment variable**:
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost/docomatic"
   ```

### 2. Environment Variables

See the [Configuration](#configuration) section below for comprehensive configuration documentation.

### 3. Database Migrations

Run database migrations to set up the schema:

```bash
# Using UV
uv run alembic upgrade head

# Using pip (if not using UV)
alembic upgrade head
```

This creates the necessary tables:
- `documents` - Top-level documents
- `sections` - Hierarchical sections
- `links` - External links to To-Do-Rama, Bucket-O-Facts, and GitHub

### 4. Verify Installation

Run tests to verify everything is set up correctly:

```bash
# Run all tests
uv run pytest

# Or using the test script
./run_tests.sh all
```

### 5. Running the HTTP SSE Server

Start the HTTP SSE server to enable agent interactions:

```bash
# Using UV
uv run uvicorn docomatic.http_api:app --host 0.0.0.0 --port 8005

# Using pip (if not using UV)
uvicorn docomatic.http_api:app --host 0.0.0.0 --port 8005
```

The server exposes:
- **Health endpoint**: `http://localhost:8005/health`
- **MCP SSE endpoint**: `http://localhost:8005/mcp/sse`

## Configuration

The Doc-O-Matic service uses **Pydantic Settings** for type-safe configuration management with support for `.env` files and environment variable overrides. This standardized approach ensures consistency across all MCP services.

### Standardized Configuration Pattern

The service uses Pydantic's `BaseSettings` with the following features:

- **`.env` file support**: Create a `.env` file in the project root for local development
- **Environment variable overrides**: All settings can be overridden via environment variables
- **Type validation**: Automatic validation of configuration values with helpful error messages
- **Default values**: Sensible defaults provided for development convenience
- **Case-insensitive**: Environment variable names are case-insensitive

Configuration is accessed via the `get_settings()` function which returns a cached singleton instance:

```python
from docomatic.config import get_settings

settings = get_settings()
db_url = settings.database_url
log_level = settings.log_level
```

### Configuration Options

#### Standardized Database Configuration

- **`database_url`** (string, default: `"sqlite:///./docomatic.db"`)
  - Database connection URL
  - Default: `sqlite:///./docomatic.db` (SQLite for local development)
  - Environment variable: `DATABASE_URL`
  - Formats:
    - SQLite: `sqlite:///./docomatic.db` or `sqlite:///path/to/docomatic.db`
    - PostgreSQL: `postgresql://user:password@host:port/database`

- **`db_pool_size`** (integer, default: `5`)
  - Connection pool size
  - Environment variable: `DB_POOL_SIZE`

- **`db_max_overflow`** (integer, default: `10`)
  - Maximum overflow connections
  - Environment variable: `DB_MAX_OVERFLOW`

- **`db_pool_timeout`** (integer, default: `30`)
  - Connection timeout in seconds
  - Environment variable: `DB_POOL_TIMEOUT`

- **`sql_echo`** (boolean, default: `false`)
  - Enable SQL query logging for debugging
  - Environment variable: `SQL_ECHO` (set to `"true"` to enable)

#### Standardized Logging Configuration

- **`log_level`** (string, default: `"INFO"`)
  - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Environment variable: `LOG_LEVEL`

- **`log_format`** (string, default: `"json"`)
  - Logging format: `"json"` or `"text"`
  - Environment variable: `LOG_FORMAT`

#### Standardized Environment Configuration

- **`environment`** (string, default: `"development"`)
  - Environment name: `"development"`, `"staging"`, `"production"`
  - Environment variable: `ENVIRONMENT`

- **`debug`** (boolean, default: `false`)
  - Enable debug mode
  - Environment variable: `DEBUG` (set to `"true"` to enable)

#### Service-Specific Configuration (Doc-O-Matic)

- **`github_token`** (string, optional, default: `None`)
  - GitHub API token for export functionality
  - Environment variable: `GITHUB_TOKEN`
  - Required only if using GitHub export features

### Configuration Examples

#### Example `.env` File for Local Development

Create a `.env` file in the project root:

```bash
# Database Configuration (SQLite)
DATABASE_URL=sqlite:///./docomatic.db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
SQL_ECHO=false

# GitHub Integration (optional)
GITHUB_TOKEN=ghp_your_token_here

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Environment Configuration
ENVIRONMENT=development
DEBUG=false
```

#### Example `.env` File for Containerized Deployment (PostgreSQL)

```bash
# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://user:password@postgres:5432/docomatic
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
SQL_ECHO=false

# GitHub Integration (optional)
GITHUB_TOKEN=ghp_your_token_here

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Environment Configuration
ENVIRONMENT=production
DEBUG=false
```

#### Example Environment Variable Overrides

Override specific settings without modifying `.env` file:

```bash
# Switch to PostgreSQL
export DATABASE_URL=postgresql://user:password@localhost/docomatic

# Enable SQL query logging
export SQL_ECHO=true

# Set GitHub token
export GITHUB_TOKEN=ghp_your_token_here

# Change log level
export LOG_LEVEL=DEBUG
```

#### Example for Different Environments

**Development (SQLite):**
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
SQL_ECHO=true
DATABASE_URL=sqlite:///./docomatic.db
```

**Production (PostgreSQL):**
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
SQL_ECHO=false
DATABASE_URL=postgresql://user:password@postgres:5432/docomatic
```

### Database Configuration

#### SQLite Configuration (Default)

The service uses SQLite by default for local development:

- **Default Path**: `./docomatic.db` (relative to project root)
- **No Setup Required**: Database file is created automatically
- **Connection URL**: `sqlite:///./docomatic.db`
- **Use Cases**: Development, testing, small deployments

#### PostgreSQL Configuration (Production)

For production deployments, use PostgreSQL:

- **Connection URL**: `postgresql://user:password@host:port/database`
- **Connection Pool**: Configured via `db_pool_size`, `db_max_overflow`, `db_pool_timeout`
- **SQL Logging**: Enable via `sql_echo=true` for debugging
- **Use Cases**: Production, high-traffic deployments, multi-user scenarios

**Database URL Helpers:**

The configuration provides helper methods to check database type:

```python
from docomatic.config import get_settings

settings = get_settings()
if settings.is_postgresql():
    # PostgreSQL-specific logic
    pass
elif settings.is_sqlite():
    # SQLite-specific logic
    pass
```

#### SQL Query Logging

Enable SQL query logging for debugging:

```bash
# In .env file
SQL_ECHO=true

# Or via environment variable
export SQL_ECHO=true
```

This will log all SQL queries to the console, useful for debugging database operations.

### GitHub Token Configuration

The `github_token` is optional and only required if using GitHub export functionality:

- **Environment Variable**: `GITHUB_TOKEN`
- **Format**: GitHub personal access token (e.g., `ghp_...`)
- **Permissions**: Requires appropriate permissions for the repositories you want to export to
- **Security**: Never commit tokens to version control; use environment variables or `.env` files (add `.env` to `.gitignore`)

### Configuration Precedence

Configuration values are resolved in the following order (highest to lowest priority):

1. **Environment variables** (highest priority)
2. **`.env` file** (if present)
3. **Default values** (lowest priority)

For example, if you set `DATABASE_URL` as an environment variable, it will override any value in the `.env` file.

### Type Validation and Error Handling

Pydantic Settings automatically validates configuration values:

- **Type checking**: Invalid types raise `ValidationError` with clear error messages
- **Required fields**: Missing required fields are detected at startup
- **Default values**: Sensible defaults are provided for optional fields

Example error message:
```
ValidationError: 1 validation error for Settings
database_url
  Field required [type=missing, input_value=None, input_type=NoneType]
```

The server handles JSON-RPC 2.0 requests via HTTP Server-Sent Events (SSE) at `/mcp/sse`.

For detailed MCP API documentation, see the [MCP API Design](#mcp-api) section below.

### 6. Containerization (Optional)

Doc-O-Matic can be containerized using Docker. For comprehensive containerization instructions, including setup, configuration, troubleshooting, and production considerations, see the [Running with Docker](#running-with-docker) section above.

The service follows the [MCP Services Containerization Standards](../agenticness/CONTAINERIZATION.md) and uses the same patterns as the [TODO service](https://github.com/rl337/todorama) and [Bucket-O-Facts](https://github.com/rl337/bucket-o-facts).

## Project Structure

```
docomatic-mcp-service/
├── README.md                    # Project overview and setup (this file)
├── AGENTS.md                    # Agent development guidelines
├── pyproject.toml              # Project configuration and dependencies
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Docker image definition
├── docomatic/                  # Main package
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── exceptions.py           # Custom exceptions
│   ├── mcp_server.py          # MCP stdio server (legacy)
│   ├── http_api.py             # HTTP SSE API server
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── document.py         # Document model
│   │   ├── section.py          # Section model
│   │   └── link.py             # Link model
│   ├── services/               # Business logic layer
│   │   ├── document_service.py # Document CRUD operations
│   │   ├── section_service.py  # Section management
│   │   ├── link_service.py     # Link management
│   │   └── export_service.py   # GitHub export
│   ├── storage/                # Data access layer
│   │   ├── database.py         # Database connection and pooling
│   │   └── repositories.py     # Repository pattern implementation
│   ├── mcp/                    # MCP tool handlers
│   │   ├── tool_handlers.py    # Tool execution logic
│   │   ├── tool_schemas.py     # Tool schema definitions
│   │   └── serializers.py      # Model serialization
│   └── migrations/             # Alembic database migrations
│       └── versions/           # Migration scripts
├── tests/                       # Test suite
│   ├── conftest.py             # Shared fixtures
│   ├── test_document_service.py
│   ├── test_section_service.py
│   ├── test_link_service.py
│   ├── test_mcp_server.py
│   ├── test_schema.py
│   ├── integration/            # Integration tests
│   └── performance/            # Performance tests
└── examples/                   # Usage examples
    └── basic_usage.py
```

## Repository Pattern

Doc-O-Matic uses the **repository pattern** for data access, providing a clean separation between business logic (services) and data access (repositories). This pattern is standardized across all MCP services for consistency and maintainability.

### Standardized Repository Pattern

The service uses repository classes that abstract database operations for core entities (Document, Section, Link). Repositories use SQLAlchemy ORM sessions and provide a clean interface for services to interact with data.

**Repository Structure:**
- Repositories are located in `docomatic/storage/repositories.py`
- Each entity type has its own repository class (e.g., `DocumentRepository`, `SectionRepository`, `LinkRepository`)
- Repositories receive SQLAlchemy `Session` via dependency injection

**Benefits:**
- **Separation of Concerns**: Business logic (services) is separated from data access (repositories)
- **Testability**: Repositories can be easily mocked for service testing
- **Maintainability**: Clear structure and responsibilities
- **Consistency**: Standard interface across all MCP services

### Repository Interface

All repositories implement standard CRUD operations:

**Core Methods:**
- `create(**kwargs)` - Create a new entity, returns entity object
- `get_by_id(entity_id)` - Get entity by ID
- `get_by_<field>(field_value)` - Get entity by unique field
- `update(entity_id, **kwargs)` - Update existing entity
- `delete(entity_id)` - Delete entity
- `list(**filters)` - List entities with optional filters
- `search(query, **filters)` - Full-text search

**Method Naming Conventions:**
- Use descriptive method names: `get_by_id()`, `get_by_document_id()`, `list()`, `search()`
- Use consistent parameter names: `entity_id`, `limit`, `offset`
- Return types: `Optional[Entity]` for single entities, `List[Entity]` for lists

**Parameter Patterns:**
- **ID Parameters**: Use `entity_id` for primary keys (str, int, or UUID)
- **Filters**: Use keyword arguments with descriptive names (e.g., `document_id`, `status`)
- **Pagination**: Use `limit` (default: 100) and `offset` (default: 0)
- **Ordering**: Use `order_by` parameter or default ordering in queries

### Service-Repository Relationship

Services use repositories via dependency injection:

```python
from docomatic.storage.repositories import DocumentRepository
from sqlalchemy.orm import Session

# Initialize repository with session
def get_document_service(session: Session):
    document_repository = DocumentRepository(session)
    return DocumentService(document_repository)

class DocumentService:
    def __init__(self, document_repository: DocumentRepository):
        self.document_repository = document_repository
    
    def create_document(self, **kwargs):
        # Business logic validation
        if not kwargs.get('title'):
            raise ValueError("Title is required")
        
        # Delegate to repository
        return self.document_repository.create(**kwargs)
```

**Separation of Concerns:**
- **Repositories**: Handle database operations (queries, transactions)
- **Services**: Handle business logic (validation, orchestration, computed fields)
- **Clear Boundaries**: Services never directly access database; repositories never contain business logic

### Examples

**Example: DocumentRepository Usage**

```python
from docomatic.storage.repositories import DocumentRepository
from sqlalchemy.orm import Session

# Initialize with session
with db.session() as session:
    doc_repo = DocumentRepository(session)
    
    # Create a document
    document = doc_repo.create(
        title="API Documentation",
        content="# API Documentation\n\n..."
    )
    
    # Get document by ID
    doc = doc_repo.get_by_id(document.id)
    
    # List documents with pagination
    documents = doc_repo.get_all(limit=50, offset=0)
    
    # Search documents
    results = doc_repo.search_by_title("API", limit=20)
```

**Example: Testing with Repository Mocks**

```python
from unittest.mock import Mock
from docomatic.services.document_service import DocumentService

def test_document_service():
    # Create mock repository
    mock_repo = Mock(spec=DocumentRepository)
    mock_repo.create.return_value = Document(id="doc-1", title="Test")
    mock_repo.get_by_id.return_value = Document(id="doc-1", title="Test")
    
    # Initialize service with mock
    service = DocumentService(mock_repo)
    
    # Test service methods
    doc = service.create_document(title="Test", content="...")
    assert doc.title == "Test"
```

### Repository Code

Repository implementations are located in:
- **File**: `docomatic/storage/repositories.py`
- **Classes**: `DocumentRepository`, `SectionRepository`, `LinkRepository`

For the complete repository template and best practices, see [REPOSITORY_PATTERN.md](../../agenticness/REPOSITORY_PATTERN.md).

## Database Migrations

Doc-O-Matic uses **Alembic** for database schema migrations, providing version control and rollback capabilities for database changes. This standardized approach is used across all MCP services for consistency and maintainability.

### Standardized Migration Approach

The service uses Alembic for managing database schema changes. All schema modifications are tracked through migration scripts, enabling:
- **Version Control**: Track all schema changes over time
- **Rollback Support**: Ability to rollback migrations if needed
- **Team Collaboration**: Standard workflow for multiple developers
- **Testing**: Test migrations in isolation before applying to production

**Alembic Directory Structure:**
- `docomatic/migrations/` - Alembic migration directory
- `docomatic/migrations/versions/` - Migration script files
- `docomatic/migrations/env.py` - Alembic environment configuration
- `docomatic/storage/alembic.ini` - Alembic configuration file

**SQLite and PostgreSQL Support:**
The service supports both SQLite (local development) and PostgreSQL (production). Migrations work with both database types.

### Migration Commands

**Apply Migrations:**
```bash
# Apply all pending migrations
alembic upgrade head

# Apply migrations up to a specific revision
alembic upgrade <revision>

# Apply one migration at a time
alembic upgrade +1
```

**Rollback Migrations:**
```bash
# Rollback last migration
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision>

# Rollback all migrations (use with caution)
alembic downgrade base
```

**Check Migration Status:**
```bash
# Show current migration version
alembic current

# Show migration history
alembic history

# Show detailed history with revisions
alembic history --verbose
```

**Create New Migration:**
```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "description of changes"

# Create empty migration script (manual)
alembic revision -m "description of changes"
```

### Examples

**Local Development (SQLite):**
```bash
# Set database path
export DATABASE_URL=sqlite:///./data/docomatic.db

# Apply all migrations
cd docomatic/storage
alembic upgrade head

# Check current version
alembic current

# Create new migration after model changes
alembic revision --autogenerate -m "add new column to documents"
```

**Containerized Deployment (PostgreSQL):**
```bash
# Set database connection
export DATABASE_URL=postgresql://postgres:postgres@postgresql:5432/docomatic

# Apply migrations in container
docker exec -it doc-o-matic alembic upgrade head

# Or run migrations before starting service
cd docomatic/storage
alembic upgrade head
python -m docomatic.mcp_server
```

**Creating a New Migration:**
```bash
# 1. Make changes to models in docomatic/models/
# 2. Generate migration automatically
cd docomatic/storage
alembic revision --autogenerate -m "add metadata column to sections"

# 3. Review the generated migration in docomatic/migrations/versions/
# 4. Edit if needed (add data migrations, custom logic)
# 5. Test the migration
alembic upgrade head
alembic downgrade -1  # Test rollback
alembic upgrade head   # Re-apply
```

**Testing Migrations:**
```bash
# Test migration on a copy of production database
cp production.db test.db
export DATABASE_URL=sqlite:///./test.db
cd docomatic/storage
alembic upgrade head

# Verify schema changes
sqlite3 test.db ".schema documents"

# Test rollback
alembic downgrade -1
alembic upgrade head
```

### Troubleshooting

**Common Migration Errors:**

1. **"Target database is not up to date"**
   ```bash
   # Check current version
   alembic current
   
   # Apply pending migrations
   alembic upgrade head
   ```

2. **"Can't locate revision identified by 'xyz'"**
   - Migration history mismatch - check `alembic_version` table
   - May need to manually set version: `alembic stamp <revision>`

3. **"Multiple heads detected"**
   - Multiple migration branches exist
   - Merge branches: `alembic merge -m "merge branches" heads`

4. **Migration conflicts with existing schema**
   - Review migration script for conflicts
   - May need to adjust migration or manually fix schema
   - Use `alembic revision --autogenerate` to detect differences

**Checking Migration Status:**
```bash
# Show current database version
alembic current

# Compare with latest migration
alembic heads

# Show pending migrations
alembic history | head -5
```

**Rollback Procedures:**
```bash
# Rollback last migration (safe)
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# Verify rollback
alembic current

# Re-apply if needed
alembic upgrade head
```

**Resolving Migration Conflicts:**
1. Check migration history: `alembic history`
2. Identify conflicting migrations
3. Review migration scripts in `docomatic/migrations/versions/`
4. Merge branches if needed: `alembic merge -m "merge" <rev1> <rev2>`
5. Test merged migration: `alembic upgrade head`

### Service-Specific Notes

**SQLite and PostgreSQL Support:**
- Migrations work with both SQLite (local development) and PostgreSQL (production)
- Some PostgreSQL-specific features (e.g., full-text search with tsvector) may require conditional logic in migrations
- Test migrations on both database types when possible

**Hierarchical Section Structure:**
- Section migrations handle parent-child relationships
- Tree structure queries may require special handling in migrations

### Migration Best Practices

1. **Always Review Auto-Generated Migrations**
   - `alembic revision --autogenerate` is a starting point
   - Review and edit migration scripts before applying
   - Add data migrations if schema changes require data transformation

2. **Test Migrations Before Production**
   - Test on a copy of production database
   - Test both upgrade and downgrade paths
   - Verify data integrity after migrations

3. **Use Descriptive Migration Messages**
   - Clear, descriptive messages: `"add order_index to sections"`
   - Avoid vague messages: `"update schema"`

4. **Keep Migrations Small and Focused**
   - One logical change per migration when possible
   - Easier to review, test, and rollback

5. **Document Complex Migrations**
   - Add comments in migration scripts for complex logic
   - Document data transformations
   - Note any manual steps required

For more information, see the [Alembic documentation](https://alembic.sqlalchemy.org/).

## Related Projects

Doc-O-Matic is part of a suite of agent-friendly tools:

- **[To-Do-Rama](https://github.com/rl337/todorama)** - Task management system for AI agents
- **[Bucket-O-Facts](https://github.com/rl337/bucketofacts)** - Fact storage and retrieval system

## Quick Start

### Create Your First Document

```python
from docomatic.storage.database import get_db
from docomatic.services.document_service import DocumentService

# Get database instance
db = get_db()

# Create a document
with db.session() as session:
    service = DocumentService(session)
    
    # Create document with initial sections
    doc = service.create_document(
        title="My First Document",
        metadata={"author": "John Doe"},
        initial_sections=[
            {
                "heading": "Introduction",
                "body": "This is the introduction section.",
                "order_index": 0
            },
            {
                "heading": "Getting Started",
                "body": "Here's how to get started...",
                "order_index": 1
            }
        ]
    )
    
    print(f"Created document: {doc.id}")
```

### Using the MCP Server

The MCP server exposes all functionality to AI agents. See [MCP Server Documentation](docomatic/MCP_SERVER.md) for API details.

### Export to GitHub

```python
from docomatic.services.export_service import ExportService, ExportConfig, ExportFormat

with db.session() as session:
    export_service = ExportService(session, github_token="ghp_...")
    
    result = export_service.export_document(
        document_id="doc-001",
        repo_owner="rl337",
        repo_name="docomatic-mcp-service",
        config=ExportConfig(
            format=ExportFormat.SINGLE_FILE,
            base_path="docs",
            branch="main"
        )
    )
    
    print(f"Exported to: {result['files_created']}")
```

See [examples/basic_usage.py](examples/basic_usage.py) for more examples.

## MCP API

Doc-O-Matic exposes 24 MCP tools organized into categories:

### Document Operations (5 tools)
- `create_document`: Create a new document with title and optional initial sections
- `get_document`: Retrieve a document by ID with all sections (tree structure)
- `update_document`: Update document title or metadata
- `delete_document`: Delete a document and all its sections
- `list_documents`: List all documents with optional filtering

### Section Operations (6 tools)
- `create_section`: Create a new section in a document (with parent for nesting)
- `get_section`: Retrieve a section by ID with children
- `update_section`: Update section heading, body, or metadata
- `delete_section`: Delete a section and its children
- `get_sections_by_document`: Get all sections for a document (tree or flat)
- `search_sections`: Full-text search across section headings and bodies

### Link Operations (11 tools)
- `link_section`: Link a section to To-Do-Rama task, Bucket-O-Facts fact, or GitHub resource
- `unlink_section`: Remove a link from a section
- `get_section_links`: Get all links for a section
- `get_sections_by_link`: Find all sections linked to a specific task/fact/GitHub resource
- `link_document`: Link a document to external resources
- `unlink_document`: Remove a link from a document
- `get_document_links`: Get all links for a document
- `get_documents_by_link`: Find all documents linked to a specific resource
- `get_links_by_type`: Get all links of a specific type
- `update_link_metadata`: Update link metadata
- `generate_link_report`: Generate a comprehensive link report with statistics

### Export Operations (1 tool)
- `export_to_github`: Export a document to GitHub as Markdown file(s)

**Protocol**: The server uses JSON-RPC 2.0 over HTTP Server-Sent Events (SSE). All requests are sent to `/mcp/sse` endpoint.

**Example Request**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_document",
    "arguments": {
      "title": "My Document",
      "metadata": {"author": "John Doe"}
    }
  }
}
```

## Development

See [AGENTS.md](AGENTS.md) for comprehensive development guidelines including:
- Test-first development practices
- Code structure and organization
- Development workflow
- Common tasks and troubleshooting

### Contributing

Contributions are welcome! Please ensure that:
- Code follows project conventions (see AGENTS.md)
- Tests are included for new features
- Documentation is updated as needed
- All tests pass: `uv run pytest`
- Code is formatted: `uv run black docomatic tests`
- Linting passes: `uv run ruff check docomatic tests`

## License

MIT

## Repository

- **GitHub**: https://github.com/rl337/docomatic-mcp-service
- **Issues**: https://github.com/rl337/docomatic-mcp-service/issues
