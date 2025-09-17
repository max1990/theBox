.PHONY: help install install-dev test test-unit test-integration test-plugins test-all lint format type-check security clean build docker-build docker-test release package docs

# Default target
help:
	@echo "TheBox Development Commands"
	@echo "=========================="
	@echo ""
	@echo "Installation:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests"
	@echo "  test-integration Run integration tests"
	@echo "  test-plugins     Run plugin tests"
	@echo "  test-coverage    Run tests with coverage"
	@echo "  test-smoke       Run smoke test"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint             Run linters"
	@echo "  format           Format code"
	@echo "  type-check       Run type checker"
	@echo "  security         Run security checks"
	@echo ""
	@echo "Development:"
	@echo "  clean            Clean build artifacts"
	@echo "  build            Build application"
	@echo "  docs             Build documentation"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     Build Docker images"
	@echo "  docker-test      Test Docker images"
	@echo ""
	@echo "Release:"
	@echo "  release          Create release package"
	@echo "  package          Package for deployment"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

# Testing
test: test-unit test-integration test-plugins

test-unit:
	python scripts/run_tests.py --suite unit

test-integration:
	python scripts/run_tests.py --suite integration

test-plugins:
	python scripts/run_tests.py --suite plugins

test-all:
	python scripts/run_tests.py --coverage

test-coverage:
	python scripts/run_tests.py --coverage

test-smoke:
	python scripts/smoke_test.py

# Code Quality
lint:
	ruff check .
	bandit -r . -f json -o bandit-report.json || true

format:
	black .
	ruff check --fix .

type-check:
	mypy --ignore-missing-imports .

security:
	bandit -r . -f json -o bandit-report.json || true
	safety check --json --output safety-report.json || true

# Development
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/

build:
	python -m build

docs:
	sphinx-build -b html docs/ docs/_build/html

# Docker
docker-build:
	docker build -f Dockerfile.workstation -t thebox:workstation .
	docker build -f Dockerfile.jetson -t thebox:jetson .

docker-test:
	docker run --rm thebox:workstation python scripts/health_check.py
	docker run --rm thebox:jetson python scripts/health_check.py

# Release
release:
	python scripts/package_release.py --name "release_$(shell date +%Y%m%d)" --format zip

package:
	python scripts/package_release.py --name "field_demo_$(shell date +%Y%m%d)" --format zip

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Validation
validate:
	python scripts/validate_plugin_conformance.py --verbose

# Health check
health:
	python scripts/health_check.py

# Performance
performance:
	python scripts/performance_monitor.py

# Development server
dev:
	python app.py

# Production server
prod:
	gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Database
db-reset:
	rm -f thebox_mvp.sqlite
	python app.py

# Logs
logs:
	tail -f logs/thebox.log

# Environment
env:
	cp docs/env.sample .env

# Dependencies
deps-update:
	pip-compile requirements.in
	pip-compile requirements-dev.in
	pip-compile requirements-gpu.in
	pip-compile requirements-jetson.in

# Security scan
security-scan:
	bandit -r . -f json -o bandit-report.json
	safety check --json --output safety-report.json
	cyclonedx-py -o sbom.json

# Plugin validation
plugin-validate:
	python scripts/validate_plugin_conformance.py --verbose

# Smoke test
smoke:
	python scripts/smoke_test.py

# All checks
check: lint type-check security test-smoke validate
	@echo "All checks passed!"

# CI simulation
ci: clean install-dev lint type-check security test-all validate smoke
	@echo "CI simulation completed successfully!"

# Quick start
quickstart: install-dev env test-smoke
	@echo "Quick start completed! Run 'make dev' to start the application."

# Full setup
setup: clean install-dev env test-smoke validate
	@echo "Full setup completed! Run 'make dev' to start the application."
