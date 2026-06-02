# Makefile for Watch!fy
.PHONY: help setup backend frontend gateway test up down logs health clean install-hooks uninstall-hooks ci-local

COMPOSE_FILE := backend/docker-compose.yml

help:
	@echo "Usage:"
	@echo "  make setup          Install dependencies and setup environment"
	@echo "  make install-hooks  Install lefthook pre-commit and pre-push hooks"
	@echo "  make uninstall-hooks Remove lefthook hooks"
	@echo "  make backend        Start only backend service"
	@echo "  make frontend       Start only frontend service"
	@echo "  make up             Start all services with Docker Compose"
	@echo "  make down           Stop all services"
	@echo "  make logs           View service logs"
	@echo "  make health         Run health check"
	@echo "  make test           Run project checks"
	@echo "  make ci-local       Run the full CI matrix locally"
	@echo "  make clean          Clean up build artifacts"

setup:
	@echo "Setting up Watch!fy..."
	@echo "Backend..."
	cd backend && pip install -r requirements.txt
	@echo "Frontend..."
	cd frontend && npm install
	@echo "Setup complete!"

install-hooks:
	@command -v lefthook >/dev/null 2>&1 || { \
		echo "lefthook not found. Install with:"; \
		echo "  go install github.com/evilmartians/lefthook@latest"; \
		echo; \
		echo "Then add \$$(go env GOPATH)/bin to your PATH:"; \
		echo "  echo 'export PATH=\$$PATH:\$$(go env GOPATH)/bin' >> ~\$$HOME/.bashrc"; \
		exit 1; \
	}
	lefthook install
	@echo "Hooks installed. Pre-commit and pre-push are now active."
	@echo "Skip with --no-verify when needed: git commit --no-verify"

uninstall-hooks:
	lefthook uninstall
	@echo "Hooks removed."

backend:
	@echo "Starting backend..."
	@cd backend && uvicorn main:app --reload --port 8000

gateway:
	@echo "Starting gateway..."
	@cd backend/gateway && go run ./cmd/server

frontend:
	@echo "Starting frontend..."
	@cd frontend && npm run dev

up:
	@echo "Starting all services with Docker Compose..."
	@docker compose -f $(COMPOSE_FILE) up --build

down:
	@echo "Stopping all services..."
	@docker compose -f $(COMPOSE_FILE) down

logs:
	@echo "Tailing logs..."
	@docker compose -f $(COMPOSE_FILE) logs -f

health:
	@echo "Running health check..."
	@./health_check.sh

test:
	@cd frontend && npm run build
	@cd backend/gateway && GOCACHE=/tmp/watchfy-go-cache GOPATH=/tmp/watchfy-go go test ./...
	@cd backend && python3 -m unittest discover -s tests -v
	@python3 -m compileall -q backend

ci-local:
	@echo "─── svelte-check ───"
	@cd frontend && npm run check
	@echo "─── frontend build ───"
	@cd frontend && npm run build
	@echo "─── Python compile ───"
	@python3 -m compileall -q backend
	@echo "─── Python tests ───"
	@cd backend && python3 -m unittest discover -s tests -v
	@echo "─── Go vet ───"
	@cd backend/gateway && go vet ./...
	@echo "─── Go tests ───"
	@cd backend/gateway && go test ./... -v
	@echo "✅ All CI checks passed locally."

clean:
	@echo "Cleaning up..."
	@docker compose -f $(COMPOSE_FILE) down --volumes
	@rm -rf backend/__pycache__ backend/.pytest_cache backend/.ruff_cache
	@rm -rf frontend/node_modules frontend/.next frontend/dist
