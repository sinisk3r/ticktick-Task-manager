---
description: Create and review database migrations safely
---

Help me create or review an Alembic database migration.

When I use this command, you should:

1. **Understand the schema change**:
   - What models are being modified?
   - What fields are being added/removed/changed?
   - Are there data migrations needed (not just schema)?
   - What are the backwards compatibility implications?

2. **Review existing models**:
   - Check backend/app/models/ for current schema
   - Understand relationships and foreign keys
   - Check for existing indexes

3. **Create the migration**:
   ```bash
   # Generate migration
   cd backend
   alembic revision --autogenerate -m "description"
   ```
   - Review the generated migration file
   - Check for issues Alembic might have missed
   - Add manual data migrations if needed
   - Ensure indexes are created for foreign keys and commonly queried fields

4. **Validate the migration**:
   - Is the `upgrade()` function correct?
   - Is the `downgrade()` function safe?
   - Are there any potential data loss risks?
   - Will this cause downtime in production?

5. **Safety checks**:
   - Adding columns: Include defaults or make nullable
   - Removing columns: Warn about data loss
   - Renaming: Use two-step migration (add new, migrate data, remove old)
   - Large tables: Consider batching for performance
   - Foreign keys: Ensure referential integrity

6. **Test the migration**:
   ```bash
   # Test upgrade
   alembic upgrade head

   # Test downgrade
   alembic downgrade -1

   # Upgrade again
   alembic upgrade head
   ```

7. **Document the change**:
   - Update CLAUDE.md if schema significantly changes
   - Note any manual steps needed in production

Always prioritize data safety and backwards compatibility.
