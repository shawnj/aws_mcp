.PHONY: install test test-unit test-integration lint format clean run dev-install

# Install dependencies
install:
	pip install -r requirements.txt

# Install in development mode with dev dependencies
dev-install:
	pip install -r requirements.txt -r requirements-dev.txt
	pip install -e .

# Run all tests
test: test-unit test-integration

# Run unit tests only
test-unit:
	python -m pytest tests/test_*.py -v --ignore=tests/test_integration.py

# Run integration tests only
test-integration:
	python tests/test_integration.py

# Run tests with coverage
test-coverage:
	python -m pytest tests/ --cov=aws_mcp --cov-report=html --cov-report=term


# Run linting
lint:
	flake8 aws_mcp/ tests/
	mypy aws_mcp/

# Format code
format:
	black aws_mcp/ tests/
	isort aws_mcp/ tests/

# Clean up build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Run the server
run:
	python main.py

# Build package
build:
	python setup.py sdist bdist_wheel

# Install from local build
install-local: build
	pip install dist/*.whl
