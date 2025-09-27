export COMPOSE_BAKE = true
export DOCKER_BUILDX = 1

COMPOSE_BASE = docker-compose.yml
DEV_COMPOSE = docker-compose.dev.yml
PROD_COMPOSE = docker-compose.prod.yml
CI_COMPOSE = docker-compose.ci.yml

ENV ?= dev
BACKUP_DIR ?= backups
BACKUP_FILE ?= $(BACKUP_DIR)/refinance-$(ENV)-$(shell date +%Y%m%d-%H%M%S).sql
DB_USER ?= postgres
DB_NAME ?= refinance

ifeq ($(ENV),prod)
COMPOSE_ARGS = -f $(COMPOSE_BASE) -f $(PROD_COMPOSE)
else ifeq ($(ENV),dev)
COMPOSE_ARGS = -f $(COMPOSE_BASE) -f $(DEV_COMPOSE)
else
$(error Unsupported ENV '$(ENV)'. Use ENV=dev or ENV=prod)
endif

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

.PHONY: db-backup db-restore prod-db-backup prod-db-restore dev-db-backup dev-db-restore

db-backup:
	@mkdir -p $(dir $(BACKUP_FILE))
	@echo "Backing up $(ENV) database to $(BACKUP_FILE)"
	docker compose $(COMPOSE_ARGS) exec -T db pg_dump -U $(DB_USER) -d $(DB_NAME) > $(BACKUP_FILE)

db-restore:
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Usage: make db-restore ENV=<dev|prod> BACKUP_FILE=<path-to-backup.sql>"; exit 1; fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then echo "Backup file $(BACKUP_FILE) not found"; exit 1; fi
	@echo "Restoring $(ENV) database from $(BACKUP_FILE)"
	docker compose $(COMPOSE_ARGS) exec -T db psql -U $(DB_USER) -d $(DB_NAME) < $(BACKUP_FILE)

prod-db-backup:
	$(MAKE) db-backup ENV=prod

prod-db-restore:
	$(MAKE) db-restore ENV=prod

dev-db-backup:
	$(MAKE) db-backup ENV=dev

dev-db-restore:
	$(MAKE) db-restore ENV=dev

.PHONY: add-entity
add-entity:
	# Example: make add-entity NAME=skywinder TELEGRAM_ID=123456789 ID=201
	@if [ -z "$(NAME)" ]; then echo "Usage: make add-entity NAME=<name> [TELEGRAM_ID=<id>] [ID=<id>]"; exit 1; fi
	docker compose -f $(COMPOSE_BASE) -f $(DEV_COMPOSE) exec api python -m app.scripts.add_entity --name "$(NAME)" $(if $(ID),--id $(ID),) $(if $(TELEGRAM_ID),--telegram-id $(TELEGRAM_ID),)
