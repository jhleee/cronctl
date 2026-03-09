setup:
	./scripts/bootstrap.sh

lint:
	ruff check src tests

test:
	PYTHONPATH=src pytest -q

doctor:
	PYTHONPATH=src python -m cronctl doctor --json

mcp-example:
	cp .mcp.json.example .mcp.json
