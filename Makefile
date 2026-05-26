# Makefile for Watch!fy
.PHONY: help setup backend frontend test clean

help:
	@echo "Usage:"
	@echo "  make setup        Install dependencies and setup environment"
	@echo "  make backend      Start only backend service"
	@echo "  make frontend     Start only frontend service"
	@echo "  make up           Start all services with Docker Compose"
	@echo "  make down         Stop all services"
	@echo "  make logs         View logs"
	@echo "  make health       Run health check"
@echo "  make test          Run tests (if any)"
@echo "  make clean         Clean up build artifacts"

setup:
	@echo "Setting up Watch!fy..."
	@echo "Backend..."
	cd backend && pip install -r requirements.txt
	@echo "Frontend..."
	cd frontend && npm install
	@echo "Setup complete!"

backend:
	@echo "Starting backend..."
	@cd backend && uvicorn black:app --reload --port 8000

frontend:
	@echo "Starting frontend..."
	@cd frontend && npm run dev

up:
	@echo "Starting all services with Docker Compose..."
	@docker-compose up --build

down:
	@echo "Stopping all services..."
	@docker-compose down

logs:
	@echo "Tailing logs..."
	@docker-compose logs -f

health:
	@echo "Running health check..."
	@./health_check.sh

test:
	@echo "No tests implemented yet."

clean:
	@echo "Cleaning up..."
	@docker-compose down --volumes
	@rm -rf backend/__pycache__ backend/.pytest_cache backend/.ruff_cache
	@rm -rf frontend/node_modules frontend/.next frontend/dist