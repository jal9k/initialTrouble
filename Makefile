# TechTime - Makefile
# Manages both backend (Python/FastAPI) and frontend (Next.js)

.PHONY: help install install-backend install-frontend \
        dev dev-backend dev-frontend \
        build build-backend build-frontend \
        test test-backend test-frontend \
        lint lint-backend lint-frontend \
        clean clean-backend clean-frontend \
        format all

# Colors for terminal output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Paths
FRONTEND_DIR := frontend/techtime
BACKEND_DIR := backend

# Default target
.DEFAULT_GOAL := help

##@ General

help: ## Display this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n${BLUE}Usage:${NC}\n  make ${GREEN}<target>${NC}\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  ${GREEN}%-20s${NC} %s\n", $$1, $$2 } /^##@/ { printf "\n${YELLOW}%s${NC}\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend Python dependencies
	@echo "${BLUE}Installing backend dependencies...${NC}"
	pip install -e ".[dev]"
	@echo "${GREEN}✓ Backend dependencies installed${NC}"

install-frontend: ## Install frontend Node.js dependencies
	@echo "${BLUE}Installing frontend dependencies...${NC}"
	cd $(FRONTEND_DIR) && npm install
	@echo "${GREEN}✓ Frontend dependencies installed${NC}"

install-conda: ## Create/update conda environment
	@echo "${BLUE}Creating conda environment...${NC}"
	conda env create -f environment.yml || conda env update -f environment.yml
	@echo "${GREEN}✓ Conda environment ready${NC}"

##@ Development

dev: ## Run both backend and frontend in development mode (requires tmux or separate terminals)
	@echo "${YELLOW}Starting development servers...${NC}"
	@echo "${BLUE}Run these commands in separate terminals:${NC}"
	@echo "  make dev-backend"
	@echo "  make dev-frontend"

dev-backend: ## Run backend development server
	@echo "${BLUE}Starting backend server on http://localhost:8000${NC}"
	python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend development server
	@echo "${BLUE}Starting frontend server on http://localhost:3000${NC}"
	cd $(FRONTEND_DIR) && npm run dev

##@ Build

build: build-backend build-frontend ## Build both backend and frontend

build-backend: ## Build backend package
	@echo "${BLUE}Building backend package...${NC}"
	pip install build
	python -m build
	@echo "${GREEN}✓ Backend build complete${NC}"

build-frontend: ## Build frontend for production
	@echo "${BLUE}Building frontend for production...${NC}"
	cd $(FRONTEND_DIR) && npm run build
	@echo "${GREEN}✓ Frontend build complete${NC}"

##@ Testing

test: test-backend ## Run all tests

test-backend: ## Run backend tests
	@echo "${BLUE}Running backend tests...${NC}"
	pytest $(BACKEND_DIR)/tests -v

test-backend-cov: ## Run backend tests with coverage
	@echo "${BLUE}Running backend tests with coverage...${NC}"
	pytest $(BACKEND_DIR)/tests -v --cov=$(BACKEND_DIR) --cov-report=html --cov-report=term

test-frontend: ## Run frontend tests (if configured)
	@echo "${BLUE}Running frontend tests...${NC}"
	cd $(FRONTEND_DIR) && npm test 2>/dev/null || echo "${YELLOW}No test script configured${NC}"

##@ Linting & Formatting

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend Python code
	@echo "${BLUE}Linting backend code...${NC}"
	ruff check $(BACKEND_DIR) analytics

lint-frontend: ## Lint frontend TypeScript code
	@echo "${BLUE}Linting frontend code...${NC}"
	cd $(FRONTEND_DIR) && npm run lint

format: ## Format backend Python code
	@echo "${BLUE}Formatting backend code...${NC}"
	ruff format $(BACKEND_DIR) analytics
	ruff check --fix $(BACKEND_DIR) analytics
	@echo "${GREEN}✓ Code formatted${NC}"

##@ CLI

cli: ## Run the TechTime CLI
	@python -m backend.cli

cli-install: ## Install the CLI tool globally
	pip install -e .
	@echo "${GREEN}✓ CLI installed. Run 'techtime' to use.${NC}"

##@ Cleanup

clean: clean-backend clean-frontend ## Clean all build artifacts

clean-backend: ## Clean backend build artifacts
	@echo "${BLUE}Cleaning backend...${NC}"
	rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "${GREEN}✓ Backend cleaned${NC}"

clean-frontend: ## Clean frontend build artifacts
	@echo "${BLUE}Cleaning frontend...${NC}"
	cd $(FRONTEND_DIR) && rm -rf .next out node_modules/.cache
	@echo "${GREEN}✓ Frontend cleaned${NC}"

clean-all: clean ## Deep clean including node_modules
	@echo "${BLUE}Deep cleaning...${NC}"
	cd $(FRONTEND_DIR) && rm -rf node_modules
	@echo "${GREEN}✓ Deep clean complete${NC}"

##@ Production

start-frontend: ## Start frontend production server
	@echo "${BLUE}Starting frontend production server...${NC}"
	cd $(FRONTEND_DIR) && npm run start

##@ Docker (if applicable)

docker-build: ## Build Docker images
	@echo "${BLUE}Building Docker images...${NC}"
	docker-compose build

docker-up: ## Start Docker containers
	@echo "${BLUE}Starting Docker containers...${NC}"
	docker-compose up -d

docker-down: ## Stop Docker containers
	@echo "${BLUE}Stopping Docker containers...${NC}"
	docker-compose down

##@ Utilities

check-deps: ## Check if required tools are installed
	@echo "${BLUE}Checking dependencies...${NC}"
	@command -v python >/dev/null 2>&1 && echo "${GREEN}✓ Python:${NC} $$(python --version)" || echo "${RED}✗ Python not found${NC}"
	@command -v pip >/dev/null 2>&1 && echo "${GREEN}✓ Pip:${NC} $$(pip --version | cut -d' ' -f1-2)" || echo "${RED}✗ Pip not found${NC}"
	@command -v node >/dev/null 2>&1 && echo "${GREEN}✓ Node:${NC} $$(node --version)" || echo "${RED}✗ Node.js not found${NC}"
	@command -v npm >/dev/null 2>&1 && echo "${GREEN}✓ NPM:${NC} $$(npm --version)" || echo "${RED}✗ NPM not found${NC}"
	@command -v ruff >/dev/null 2>&1 && echo "${GREEN}✓ Ruff:${NC} $$(ruff --version)" || echo "${YELLOW}! Ruff not found (install with: pip install ruff)${NC}"

logs: ## Show backend logs
	@tail -f data/logs/*.log 2>/dev/null || echo "${YELLOW}No logs found${NC}"

reset-db: ## Reset the analytics database
	@echo "${YELLOW}Resetting analytics database...${NC}"
	rm -f data/analytics.db
	@echo "${GREEN}✓ Database reset${NC}"

