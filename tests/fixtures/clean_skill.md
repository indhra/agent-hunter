---
name: "fastapi-migrations"
description: "Manage Alembic database migrations for FastAPI projects."
version: "1.2.0"
license: "MIT"
author: "example-author"
compatibility:
  claude: ">=1.0.0"
triggers:
  - "run database migration"
  - "create alembic migration"
  - "apply database schema changes"
mcp_dependencies: []
---

# fastapi-migrations

A skill for managing Alembic database migrations in FastAPI projects.

## When to Use

When the user asks to:
- Create a new migration
- Apply pending migrations
- Check migration status
- Rollback a migration

## Instructions

1. Ask the user which environment (dev/staging/prod).
2. Show the current migration status using `alembic current`.
3. If creating a migration, ask for a descriptive name.
4. Generate the migration command with the appropriate flags.
5. Show a preview of what will run before executing.

## Examples

**User:** Create a new migration for adding user_roles table

**Response:**
I'll create a new Alembic migration for the user_roles table.

```bash
alembic revision --autogenerate -m "add_user_roles_table"
```

Review the generated file in `alembic/versions/` before applying.
To apply: `alembic upgrade head`
