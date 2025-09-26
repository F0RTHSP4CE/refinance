export COMPOSE_BAKE = true
export DOCKER_BUILDX = 1

COMPOSE_BASE = docker-compose.yml
DEV_COMPOSE = docker-compose.dev.yml
PROD_COMPOSE = docker-compose.prod.yml
CI_COMPOSE = docker-compose.ci.yml
BACKUP_DIR ?= backups
BACKUP_FILE ?= $(BACKUP_DIR)/refinance-$(shell date +%Y%m%d-%H%M%S).sql

.PHONY: dev prod ci down

# Starts the development environment (services with reload, volumes, etc.)
dev:
	docker compose -f $(COMPOSE_BASE) -f $(DEV_COMPOSE) up --build

dev-daemon:
	docker compose -f $(COMPOSE_BASE) -f $(DEV_COMPOSE) up --build -d

# Starts the production environment
prod:
	docker compose -f $(COMPOSE_BASE) -f $(PROD_COMPOSE) up --build

prod-daemon:
	docker compose -f $(COMPOSE_BASE) -f $(PROD_COMPOSE) up --build -d


# Starts the CI environment
ci-daemon:
	docker compose -f $(COMPOSE_BASE) -f $(CI_COMPOSE) up --build -d

ci-test:
	docker compose -f $(COMPOSE_BASE) -f $(CI_COMPOSE) exec api pytest -v -s --log-level DEBUG

ci-down:
	docker compose -f $(COMPOSE_BASE) -f $(CI_COMPOSE) down

# Stops all running services
down:
	docker compose -f $(COMPOSE_BASE) -f $(DEV_COMPOSE) -f $(PROD_COMPOSE) down

test: dev-daemon
	docker compose -f $(COMPOSE_BASE) -f $(DEV_COMPOSE) exec api pytest
	make down

.PHONY: prod-db-backup prod-db-restore

prod-db-backup:
	@mkdir -p $(dir $(BACKUP_FILE))
	@echo "Backing up database to $(BACKUP_FILE)"
	docker compose -f $(COMPOSE_BASE) -f $(PROD_COMPOSE) exec -T db pg_dump -U postgres -d refinance > $(BACKUP_FILE)

prod-db-restore:
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Usage: make prod-db-restore BACKUP_FILE=<path-to-backup.sql>"; exit 1; fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then echo "Backup file $(BACKUP_FILE) not found"; exit 1; fi
	@echo "Restoring database from $(BACKUP_FILE)"
	docker compose -f $(COMPOSE_BASE) -f $(PROD_COMPOSE) exec -T db psql -U postgres -d refinance < $(BACKUP_FILE)

.PHONY: add-entity
add-entity:
	# Example: make add-entity NAME=skywinder TELEGRAM_ID=123456789 ID=201
	@if [ -z "$(NAME)" ]; then echo "Usage: make add-entity NAME=<name> [TELEGRAM_ID=<id>] [ID=<id>]"; exit 1; fi
	docker compose -f $(COMPOSE_BASE) -f $(DEV_COMPOSE) exec api python -m app.scripts.add_entity --name "$(NAME)" $(if $(ID),--id $(ID),) $(if $(TELEGRAM_ID),--telegram-id $(TELEGRAM_ID),)
