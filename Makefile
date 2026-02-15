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

COMPOSE_SUFFIX_dev = $(DEV_COMPOSE)
COMPOSE_SUFFIX_prod = $(PROD_COMPOSE)
COMPOSE_SUFFIX_ci = $(CI_COMPOSE)

COMPOSE = docker compose -f $(COMPOSE_BASE) -f $(or $(COMPOSE_SUFFIX_$(ENV)),$(error Unsupported ENV '$(ENV)'. Use ENV=dev, ENV=prod, or ENV=ci))

.ONESHELL:

.PHONY: dev prod up up-detached down test ci db-backup db-restore add-entity dev-ui-new

dev: ENV = dev
dev:
	(cd ui-new && npm run dev) &
	$(COMPOSE) up --build

prod: ENV = prod
prod: up-detached

up:
	$(COMPOSE) up --build

up-detached:
	$(COMPOSE) up --build -d

down:
	$(COMPOSE) down

test: ENV = dev
test: up-detached
	@$(COMPOSE) exec api pytest

ci: ENV = ci
ci:
	@set -e
	@trap '$(COMPOSE) down' EXIT
	@$(COMPOSE) up --build -d
	@$(COMPOSE) exec api pytest -v -s --log-level DEBUG
	@trap - EXIT
	@$(COMPOSE) down

db-backup:
	@mkdir -p $(dir $(BACKUP_FILE))
	@echo "Backing up $(ENV) database to $(BACKUP_FILE)"
	$(COMPOSE) exec -T db pg_dump -U $(DB_USER) -d $(DB_NAME) > $(BACKUP_FILE)

db-restore:
	@if [ -z "$(BACKUP_FILE)" ]; then echo "Usage: make db-restore ENV=<dev|prod|ci> BACKUP_FILE=<path-to-backup.sql>"; exit 1; fi
	@if [ ! -f "$(BACKUP_FILE)" ]; then echo "Backup file $(BACKUP_FILE) not found"; exit 1; fi
	@echo "Dropping existing $(ENV) database $(DB_NAME)"
	$(COMPOSE) exec -T db psql -U $(DB_USER) -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$(DB_NAME)' AND pid <> pg_backend_pid();"
	$(COMPOSE) exec -T db psql -U $(DB_USER) -d postgres -c "DROP DATABASE IF EXISTS \"$(DB_NAME)\";"
	@echo "Creating fresh $(ENV) database $(DB_NAME)"
	$(COMPOSE) exec -T db psql -U $(DB_USER) -d postgres -c "CREATE DATABASE \"$(DB_NAME)\";"
	@echo "Restoring $(ENV) database from $(BACKUP_FILE)"
	$(COMPOSE) exec -T db psql -U $(DB_USER) -d $(DB_NAME) < $(BACKUP_FILE)

.PHONY: add-entity
add-entity: ENV = dev
add-entity:
	# Example: make add-entity NAME=skywinder TELEGRAM_ID=123456789 ID=201
	@if [ -z "$(NAME)" ]; then echo "Usage: make add-entity NAME=<name> [TELEGRAM_ID=<id>] [ID=<id>]"; exit 1; fi
	$(COMPOSE) exec api python -m app.scripts.add_entity --name "$(NAME)" $(if $(ID),--id $(ID),) $(if $(TELEGRAM_ID),--telegram-id $(TELEGRAM_ID),)

dev-ui-new:
	cd ui-new && npm run dev
