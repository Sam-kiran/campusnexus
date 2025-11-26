.PHONY: help install migrate run test docker-up docker-down

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies"
	@echo "  make migrate     - Run database migrations"
	@echo "  make run         - Run development server"
	@echo "  make test        - Run tests"
	@echo "  make docker-up   - Start Docker containers"
	@echo "  make docker-down - Stop Docker containers"

install:
	pip install -r requirements.txt

migrate:
	python manage.py makemigrations
	python manage.py migrate

run:
	python manage.py runserver

test:
	python manage.py test

docker-up:
	docker-compose up --build

docker-down:
	docker-compose down

