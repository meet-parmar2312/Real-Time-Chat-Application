.PHONY: help install run migrate upgrade test test-cov docker-build docker-up docker-down clean

help:
	@echo "Available commands:"
	@echo "  make install       Install dependencies"
	@echo "  make run           Run development server locally with uvicorn"
	@echo "  make migrate       Generate new Alembic migration"
	@echo "  make upgrade       Run pending database migrations"
	@echo "  make test          Run pytest suite"
	@echo "  make test-cov      Run pytest with coverage"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-up     Start all services via docker-compose"
	@echo "  make docker-down   Stop and remove docker-compose containers"
	@echo "  make clean         Remove cached files and temporary artifacts"

install:
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

migrate:
	alembic revision --autogenerate -m "auto migration"

upgrade:
	alembic upgrade head

test:
	pytest -v

test-cov:
	pytest -v --cov=app --cov-report=term-missing

docker-build:
	docker compose build

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down -v

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov dist build *.egg-info
