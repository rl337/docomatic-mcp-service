# Agent Guidelines for Doc-O-Matic

This document provides essential information for AI agents working on the Doc-O-Matic project, including development practices, code structure, and contribution guidelines.

## Core Principles

### Test-First Development (TDD)
**All agents MUST follow test-first behavior:**

1. **Write tests BEFORE implementing features**
   - Define test cases that describe expected behavior
   - Tests should initially fail (red phase)
   - Implement minimal code to make tests pass (green phase)
   - Refactor while keeping tests green

2. **Run tests before any commit**
   - Always run `uv run pytest` before committing
   - Never commit code that breaks existing tests
   - Ensure all new tests pass before pushing

3. **Test Coverage Requirements**
   - All database operations must have tests
   - All MCP API endpoints must have tests
   - All service layer methods must have tests
   - Critical paths: 100% coverage (document/section CRUD, validation)
   - Service layer: >85% coverage
   - Repository layer: >90% coverage
   - MCP handlers: >80% coverage

## Development Workflow

### Before Starting Work
1. Read the task description and acceptance criteria
2. Review existing tests related to the feature
3. Write failing tests for the new functionality
4. Ensure tests are comprehensive and cover edge cases

### During Development
1. Run tests frequently: `uv run pytest`
2. Fix failing tests immediately
3. Add tests for bugs as you discover them
4. Refactor with confidence (tests protect you)

### Before Committing
**MANDATORY**: 
1. Run `uv run pytest` - All tests must pass
   - No linting errors
   - Code coverage maintained or improved
   - Documentation updated if needed

2. **Write meaningful commit messages**
   - Commit messages MUST clearly describe what changed and why
   - Format: Use imperative mood (e.g., "Add feature X" not "Added feature X")
   - Include context: What problem does this solve? What functionality is added/changed?
   - Examples of good commit messages:
     ```
     Add HTTP SSE endpoint for MCP server
     
     Implements FastAPI-based HTTP Server-Sent Events endpoint at /mcp/sse.
     Updates Dockerfile to run uvicorn instead of stdio MCP server. Includes
     comprehensive error handling and JSON-RPC request routing.
     ```
     
     ```
     Fix SQLAlchemy metadata attribute conflict
     
     Renames 'metadata' attribute to 'meta' in Document and Section models
     to avoid conflict with SQLAlchemy's reserved 'metadata' attribute.
     Database column name remains 'metadata' for compatibility.
     ```
   - Examples of bad commit messages:
     ```
     ❌ "fix"
     ❌ "update"
     ❌ "changes"
     ❌ "wip"
     ❌ "commit"
     ```

### Before Pushing
**MANDATORY**: 
1. Run `uv run pytest` - Verify all tests pass
   - Check that the service starts correctly
   - Ensure database migrations work
   - Verify MCP tools are accessible

2. **Verify commit messages are meaningful**
   - Review your commit history: `git log --oneline -5`
   - Ensure each commit has a clear, descriptive message
   - If you have commits with poor messages, use `git commit --amend` or `git rebase -i` to fix them before pushing

3. **Rebase repeated check-ins into feature-based commits**
   - **MANDATORY**: Before pushing, review your local commit history
   - If you have multiple small commits that are part of one feature/fix, rebase them together
   - Use `git rebase -i HEAD~N` where N is the number of commits to review
   - Squash related commits into logical, feature-based commits

## Code Structure

### Directory Organization

```
docorama/
├── docomatic/              # Main package
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── exceptions.py       # Custom exceptions
│   ├── mcp_server.py       # MCP stdio server (legacy)
│   ├── http_api.py         # HTTP SSE API server
│   ├── models/             # SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── document.py
│   │   ├── section.py
│   │   └── link.py
│   ├── services/            # Business logic layer
│   │   ├── document_service.py
│   │   ├── section_service.py
│   │   ├── link_service.py
│   │   └── export_service.py
│   ├── storage/            # Data access layer
│   │   ├── database.py
│   │   └── repositories.py
│   ├── mcp/                # MCP tool handlers
│   │   ├── tool_handlers.py
│   │   ├── tool_schemas.py
│   │   └── serializers.py
│   └── migrations/         # Alembic migrations
│       └── versions/
├── tests/                  # Test suite
│   ├── conftest.py
│   ├── test_*.py
│   ├── integration/
│   └── performance/
└── examples/               # Usage examples
```

### Layer Responsibilities

#### Models Layer (`docomatic/models/`)
- Define database entities using SQLAlchemy ORM
- Define relationships (foreign keys, one-to-many, etc.)
- Define constraints and indexes
- **Note**: Use `meta` as Python attribute name for metadata (maps to `metadata` column)

#### Repository Layer (`docomatic/storage/repositories.py`)
- Abstract data access operations
- CRUD operations
- Complex queries (hierarchical, full-text search)
- Database-specific implementations (PostgreSQL vs SQLite)

#### Service Layer (`docomatic/services/`)
- Business logic and validation
- Coordinate between repositories
- Transaction management
- Error handling and transformation

#### MCP Layer (`docomatic/mcp/` and `docomatic/http_api.py`)
- HTTP SSE endpoint at `/mcp/sse`
- JSON-RPC 2.0 request handling
- Tool routing and execution
- Error formatting

## Development Practices

### Database Migrations
- Use Alembic for all schema changes
- Always review auto-generated migrations
- Test migrations up and down
- Never modify existing migration files (create new ones)

### Error Handling
- Use custom exceptions from `docomatic.exceptions`
- Convert database errors to domain exceptions
- Provide clear error messages with context

### Configuration
- Use Pydantic Settings for type-safe configuration
- Support `.env` files and environment variables
- Provide sensible defaults for development

### Testing
- Unit tests: Test individual components in isolation
- Integration tests: Test component interactions
- Performance tests: Establish baselines and verify scalability
- Use fixtures from `tests/conftest.py`

## Common Tasks

### Adding a New MCP Tool
1. Add tool schema to `docomatic/mcp/tool_schemas.py`
2. Add tool handler to `docomatic/mcp/tool_handlers.py`
3. Update `http_api.py` to handle the tool (if needed)
4. Add tests in `tests/test_mcp_server.py` or `tests/integration/`
5. Update documentation

### Adding a New Database Field
1. Update model in `docomatic/models/`
2. Create migration: `uv run alembic revision --autogenerate -m "description"`
3. Review and apply migration: `uv run alembic upgrade head`
4. Update service methods if needed
5. Add tests

### Adding a New Service Method
1. Add method to service class in `docomatic/services/`
2. Add validation and business logic
3. Delegate to repository for data access
4. Add tests in `tests/test_*_service.py`
5. Update documentation if public API

## Code Style

- **Formatting**: Use Black (line length: 100)
- **Linting**: Use Ruff (configured in `pyproject.toml`)
- **Type Checking**: Use mypy (configured in `pyproject.toml`)
- **Naming**: 
  - Classes: `PascalCase`
  - Functions/Methods: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`
  - Private: Prefix with `_`

## Dependencies

All dependencies are managed via UV and defined in `pyproject.toml`:
- Core: `mcp`, `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic-settings`
- Database: `psycopg2-binary` (PostgreSQL), SQLite (built-in)
- GitHub: `PyGithub`
- Markdown: `markdown`, `markdown-it-py`
- Dev: `pytest`, `pytest-cov`, `black`, `ruff`, `mypy`

## Running the Service

### Local Development
```bash
# Start HTTP SSE server
uv run uvicorn docomatic.http_api:app --host 0.0.0.0 --port 8005

# Or use stdio MCP server (legacy)
uv run python -m docomatic.mcp_server
```

### Docker
```bash
# Build and start
docker compose up -d

# View logs
docker compose logs -f doc-o-matic

# Run migrations
docker compose exec doc-o-matic uv run alembic upgrade head
```

## Troubleshooting

### Tests Fail with Import Errors
- Ensure dependencies are installed: `uv sync --dev`
- Check virtual environment: `uv run python -c "import docomatic"`

### Database Connection Errors
- Check `DATABASE_URL` environment variable
- Verify PostgreSQL is running (if using PostgreSQL)
- Check database permissions

### MCP Server Not Responding
- Check service logs: `docker compose logs doc-o-matic`
- Verify HTTP endpoint: `curl http://localhost:8005/health`
- Check MCP endpoint: `curl http://localhost:8005/mcp/sse`

## Additional Resources

- **README.md**: Project overview, installation, and usage
- **Architecture**: See README.md for architecture overview
- **MCP API**: See README.md for MCP tool documentation
- **Database Schema**: See README.md for database schema details


