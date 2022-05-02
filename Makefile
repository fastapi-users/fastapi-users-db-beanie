MONGODB_CONTAINER_NAME := fastapi-users-db-beanie-test-mongo

install:
	python -m pip install --upgrade pip
	pip install flit
	flit install --deps develop

isort:
	isort ./fastapi_users_db_beanie ./tests

format: isort
	black .

test:
	docker stop $(MONGODB_CONTAINER_NAME) || true
	docker run -d --rm --name $(MONGODB_CONTAINER_NAME) -p 27017:27017 mongo:4.4
	pytest --cov=fastapi_users_db_beanie/ --cov-report=term-missing --cov-fail-under=100
	docker stop $(MONGODB_CONTAINER_NAME)

bumpversion-major:
	bumpversion major

bumpversion-minor:
	bumpversion minor

bumpversion-patch:
	bumpversion patch
