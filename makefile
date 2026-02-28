.PHONY: migration-create migration-up migration-down

migration-create:
	@read -p "Enter migration message: " msg; \
	if [ -z "$$msg" ]; then \
		echo "Migration message cannot be empty."; \
		exit 1; \
	fi; \
	uv run alembic revision -m "$$msg"; \
	touch migrations/sql/up/"$$msg".sql; \
	touch migrations/sql/down/"$$msg".sql; \
	echo "Created empty SQL files:"; \
	echo "  migrations/sql/up/$$msg.sql"; \
	echo "  migrations/sql/down/$$msg.sql"

migration-up:
	uv run alembic upgrade head

migration-down:
	uv run alembic downgrade -1