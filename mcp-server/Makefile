.PHONY: help install up down test test-int test-all lint format clean logs

#Справка
help:
	@echo "🔧 PetCare MCP-Server — команды управления"
	@echo ""
	@echo "Установка: make install"
	@echo "Инфраструктура: make up / make down / make logs"
	@echo "Тесты: make test / make test-int / make test-all"
	@echo "Код: make lint / make format"
	@echo "Очистка: make clean"

#Установка
install:
	pip install -e ".[dev]" 2>/dev/null || pip install -e .

#Инфраструктура
up:
	docker compose -f docker/docker-compose.yml up -d --build

down:
	docker compose -f docker/docker-compose.yml down -v

logs:
	docker compose -f docker/docker-compose.yml logs -f api


#Запустить MCP-сервер для разработки
run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Запустить сервер в production-режиме
run-prod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

#Тесты
test:
	pytest tests/unit/ -v --tb=short

test-int:
	@docker compose -f docker/docker-compose.yml ps postgres | grep -q Up || \
	pytest tests/integration/ -v --tb=short

test-all:
	pytest tests/ -v --tb=short \
		--cov=app --cov-report=term-missing \
		--json-report --json-report-file=report.json

#Качество кода
