.PHONY: help build up down logs shell test clean train prod

ENV ?= dev

RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)MCP Job Search System - Docker Commands$(NC)"
	@echo "=========================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# ============================================================================
# Development Commands
# ============================================================================

build: 
	@echo "$(YELLOW)Building Docker images...$(NC)"
	docker-compose build

up: 
	@echo "$(GREEN)Starting development environment...$(NC)"
	docker-compose --profile dev up -d
	@echo "$(GREEN)✅ Development environment started$(NC)"
	@echo "$(BLUE)🌐 Application: http://localhost:8000$(NC)"
	@echo "$(BLUE)🍃 MongoDB Admin: http://localhost:8081 (admin/admin)$(NC)"

down: 
	@echo "$(YELLOW)Stopping all services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✅ All services stopped$(NC)"

restart: down up 

logs: 
	docker-compose logs -f

logs-app: 
	docker-compose logs -f app-dev

status: 
	docker-compose ps

# ============================================================================
# Utility Commands
# ============================================================================

shell: 
	docker-compose exec app-dev /bin/bash

shell-db: 
	docker-compose exec mongodb mongosh --username admin --password devpassword123

shell-redis: 
	docker-compose exec redis redis-cli

# ============================================================================
# Training Commands
# ============================================================================

train: 
	@echo "$(YELLOW)Starting TensorBoard and model training...$(NC)"
	@echo "$(BLUE)📊 Starting TensorBoard on http://localhost:6006$(NC)"
	docker-compose --profile training up -d trainer
	@sleep 3
	@echo "$(YELLOW)Starting training process...$(NC)"
	docker-compose exec trainer python scripts/train.py
	@echo "$(GREEN)✅ Training completed$(NC)"
	@echo "$(BLUE)📊 TensorBoard still running: http://localhost:6006$(NC)"

train-quick: 
	@echo "$(YELLOW)Starting quick training test...$(NC)"
	docker-compose exec app-dev python scripts/train.py --quick-test

tensorboard: 
	@echo "$(BLUE)Starting TensorBoard...$(NC)"
	docker-compose --profile training up -d trainer
	@echo "$(BLUE)📊 TensorBoard: http://localhost:6006$(NC)"

stop-tensorboard: 
	@echo "$(YELLOW)Stopping TensorBoard...$(NC)"
	docker-compose --profile training stop trainer
	@echo "$(GREEN)✅ TensorBoard stopped$(NC)"

jupyter: 
	@echo "$(BLUE)Starting Jupyter notebook...$(NC)"
	docker-compose --profile training up -d trainer
	@echo "$(BLUE)📓 Jupyter: http://localhost:8888$(NC)"

# ============================================================================
# Production Commands
# ============================================================================

prod: 
	@echo "$(GREEN)Starting production environment...$(NC)"
	docker-compose --profile prod up -d
	@echo "$(GREEN)✅ Production environment started$(NC)"
	@echo "$(BLUE)🌐 Application: http://localhost$(NC)"

prod-logs: 
	docker-compose --profile prod logs -f

prod-down: 
	docker-compose --profile prod down

# ============================================================================
# Database Commands
# ============================================================================

db-backup: 
	@echo "$(YELLOW)Creating database backup...$(NC)"
	mkdir -p ./backups
	docker-compose exec mongodb mongodump --username admin --password devpassword123 --authenticationDatabase admin --out /tmp/backup
	docker cp mcp-mongodb:/tmp/backup ./backups/mongodb-$(shell date +%Y%m%d-%H%M%S)
	@echo "$(GREEN)✅ Database backup created$(NC)"

db-restore: 
	@if [ -z "$(BACKUP_DIR)" ]; then echo "$(RED)Please specify BACKUP_DIR=path/to/backup$(NC)"; exit 1; fi
	@echo "$(YELLOW)Restoring database from $(BACKUP_DIR)...$(NC)"
	docker cp $(BACKUP_DIR) mcp-mongodb:/tmp/restore
	docker-compose exec mongodb mongorestore --username admin --password devpassword123 --authenticationDatabase admin /tmp/restore
	@echo "$(GREEN)✅ Database restored$(NC)"

db-seed: 
	@echo "$(YELLOW)Seeding database with sample data...$(NC)"
	docker-compose exec app-dev python scripts/seed_database.py
	@echo "$(GREEN)✅ Database seeded$(NC)"

# ============================================================================
# Testing Commands
# ============================================================================

test: 
	@echo "$(YELLOW)Running tests...$(NC)"
	docker-compose exec app-dev python -m pytest tests/ -v
	@echo "$(GREEN)✅ Tests completed$(NC)"

test-scraper: 
	docker-compose exec app-dev python -m pytest tests/test_data_collection.py -v

test-model:
	docker-compose exec app-dev python -m pytest tests/test_model_manager.py -v

test-api: 
	docker-compose exec app-dev python -m pytest tests/test_inference.py -v

# ============================================================================
# Maintenance Commands
# ============================================================================

clean: 
	@echo "$(YELLOW)Cleaning up Docker resources...$(NC)"
	docker-compose down -v
	docker system prune -f
	docker volume prune -f
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

clean-all: 
	@echo "$(RED)⚠️  This will remove ALL Docker resources!$(NC)"
	@read -p "Are you sure? (y/N) " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker system prune -af; \
		docker volume prune -f; \
		echo "$(GREEN)✅ Complete cleanup done$(NC)"; \
	fi

update: 
	@echo "$(YELLOW)Updating and rebuilding...$(NC)"
	docker-compose down
	docker-compose build --no-cache
	docker-compose --profile dev up -d
	@echo "$(GREEN)✅ Update completed$(NC)"

# ============================================================================
# Development Shortcuts
# ============================================================================

dev: build up 

install: 
	@echo "$(BLUE)Setting up MCP Job Search System...$(NC)"
	cp .env.example .env
	@echo "$(YELLOW)Please edit .env with your configuration$(NC)"
	make build
	make up
	make db-seed
	@echo "$(GREEN)✅ Setup completed!$(NC)"
	@echo "$(BLUE)🌐 Visit: http://localhost:8000$(NC)"

# ============================================================================
# Monitoring
# ============================================================================

stats:
	docker stats

ps: 
	docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# ============================================================================
# GPU/CUDA Commands
# ============================================================================

gpu-test: 
	docker-compose exec app-dev python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"

nvidia-smi:
	docker-compose exec app-dev nvidia-smi 
