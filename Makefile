# TechTime - Makefile
# Manages both backend (Python/FastAPI) and frontend (Next.js)

.PHONY: help install install-backend install-frontend install-all \
        dev dev-backend dev-frontend dev-desktop dev-server \
        build build-backend build-frontend build-app \
        test test-backend test-frontend test-cov test-unit test-integration \
        lint lint-backend lint-frontend typecheck quality \
        clean clean-backend clean-frontend clean-all \
        format download-ollama dist-macos dist-windows

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

install: install-backend install-frontend ## Install backend and frontend dependencies

install-all: ## Install all dependencies (backend + desktop + frontend)
	@echo "${BLUE}Installing all dependencies...${NC}"
	pip install -e ".[all]"
	cd $(FRONTEND_DIR) && npm install
	@echo "${GREEN}✓ All dependencies installed${NC}"

install-backend: ## Install backend Python dependencies
	@echo "${BLUE}Installing backend dependencies...${NC}"
	pip install -e ".[server,dev]"
	@echo "${GREEN}✓ Backend dependencies installed${NC}"

install-desktop: ## Install desktop application dependencies
	@echo "${BLUE}Installing desktop dependencies...${NC}"
	pip install -e ".[desktop,dev]"
	@echo "${GREEN}✓ Desktop dependencies installed${NC}"

install-frontend: ## Install frontend Node.js dependencies
	@echo "${BLUE}Installing frontend dependencies...${NC}"
	cd $(FRONTEND_DIR) && npm install
	@echo "${GREEN}✓ Frontend dependencies installed${NC}"

install-conda: ## Create/update conda environment
	@echo "${BLUE}Creating conda environment...${NC}"
	conda env create -f environment.yml || conda env update -f environment.yml
	@echo "${GREEN}✓ Conda environment ready${NC}"

##@ Development

dev: ## Show development mode options
	@echo "${YELLOW}Development Modes:${NC}"
	@echo ""
	@echo "${BLUE}Desktop App with Hot Reload (Recommended):${NC}"
	@echo "  Terminal 1: make dev-frontend"
	@echo "  Terminal 2: make dev-desktop"
	@echo ""
	@echo "${BLUE}Backend Server Only:${NC}"
	@echo "  Terminal 1: make dev-server"
	@echo "  Terminal 2: make dev-frontend"

dev-backend: dev-server ## Alias for dev-server

dev-server: ## Run FastAPI backend server with hot reload
	@echo "${BLUE}Starting backend server on http://localhost:8000${NC}"
	python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Run frontend Next.js development server
	@echo "${BLUE}Starting frontend server on http://localhost:3000${NC}"
	cd $(FRONTEND_DIR) && npm run dev

dev-desktop: ## Run desktop app in development mode (uses Next.js dev server)
	@echo "${BLUE}Starting desktop app in dev mode...${NC}"
	@echo "${YELLOW}Make sure 'make dev-frontend' is running in another terminal!${NC}"
	python desktop_main.py --dev --debug

##@ Build

build: build-frontend build-app ## Full production build (frontend + desktop app)
	@echo "${GREEN}✓ Build complete! Output in dist/${NC}"

build-backend: ## Build backend Python package
	@echo "${BLUE}Building backend package...${NC}"
	pip install build
	python -m build
	@echo "${GREEN}✓ Backend build complete${NC}"

build-frontend: ## Build frontend for production (static export)
	@echo "${BLUE}Building frontend for production...${NC}"
	cd $(FRONTEND_DIR) && npm run build
	@echo "${GREEN}✓ Frontend build complete${NC}"

build-app: ## Build desktop app with PyInstaller (assumes frontend is built)
	@echo "${BLUE}Building desktop application...${NC}"
	python scripts/build_app.py --skip-frontend
	@echo "${GREEN}✓ Desktop app build complete${NC}"

download-ollama: ## Download Ollama binaries for bundling
	@echo "${BLUE}Downloading Ollama binaries...${NC}"
	python scripts/download_ollama.py
	@echo "${GREEN}✓ Ollama downloaded${NC}"

##@ Testing

test: ## Run all tests
	@echo "${BLUE}Running all tests...${NC}"
	pytest tests/ -v

test-backend: ## Run backend tests only
	@echo "${BLUE}Running backend tests...${NC}"
	pytest $(BACKEND_DIR)/tests -v

test-cov: ## Run tests with coverage report
	@echo "${BLUE}Running tests with coverage...${NC}"
	pytest tests/ --cov=backend --cov=desktop --cov=analytics --cov-report=html --cov-report=term
	@echo "${GREEN}Coverage report: htmlcov/index.html${NC}"

test-unit: ## Run unit tests only
	@echo "${BLUE}Running unit tests...${NC}"
	pytest tests/unit/ -v

test-integration: ## Run integration tests only
	@echo "${BLUE}Running integration tests...${NC}"
	pytest tests/integration/ -v

test-frontend: ## Run frontend tests (if configured)
	@echo "${BLUE}Running frontend tests...${NC}"
	cd $(FRONTEND_DIR) && npm test 2>/dev/null || echo "${YELLOW}No test script configured${NC}"

##@ Linting & Formatting

lint: lint-backend lint-frontend ## Run all linters

lint-backend: ## Lint backend Python code
	@echo "${BLUE}Linting backend code...${NC}"
	ruff check $(BACKEND_DIR) desktop analytics

lint-frontend: ## Lint frontend TypeScript code
	@echo "${BLUE}Linting frontend code...${NC}"
	cd $(FRONTEND_DIR) && npm run lint

format: ## Format backend Python code
	@echo "${BLUE}Formatting backend code...${NC}"
	ruff format $(BACKEND_DIR) desktop analytics
	ruff check --fix $(BACKEND_DIR) desktop analytics
	@echo "${GREEN}✓ Code formatted${NC}"

typecheck: ## Run type checker on Python code
	@echo "${BLUE}Running type checker...${NC}"
	mypy $(BACKEND_DIR)/ desktop/ --ignore-missing-imports
	@echo "${GREEN}✓ Type check complete${NC}"

quality: lint typecheck ## Run all quality checks (lint + typecheck)

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

clean-all: clean ## Deep clean including node_modules and downloaded resources
	@echo "${BLUE}Deep cleaning...${NC}"
	rm -rf .venv/
	cd $(FRONTEND_DIR) && rm -rf node_modules
	rm -rf resources/ollama/
	rm -rf htmlcov/
	rm -rf .coverage
	@echo "${GREEN}✓ Deep clean complete${NC}"

##@ Distribution

dist-macos: build ## Create macOS distribution (DMG)
	@echo "${BLUE}Creating macOS distribution...${NC}"
	python scripts/distribute_macos.py --dmg
	@echo "${GREEN}✓ macOS distribution created${NC}"

dist-windows: build ## Create Windows distribution (installer)
	@echo "${BLUE}Creating Windows distribution...${NC}"
	python scripts/distribute_windows.py
	@echo "${GREEN}✓ Windows distribution created${NC}"

dist: dist-macos dist-windows ## Create all distributions

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

