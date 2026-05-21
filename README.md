# petstore-mcp

[![CI](https://github.com/RamonAlcantaraArceo/petstore-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/RamonAlcantaraArceo/petstore-mcp/actions/workflows/ci.yml)
[![Docs](https://github.com/RamonAlcantaraArceo/petstore-mcp/actions/workflows/docs.yml/badge.svg)](https://github.com/RamonAlcantaraArceo/petstore-mcp/actions/workflows/docs.yml)
[![codecov](https://codecov.io/gh/RamonAlcantaraArceo/petstore-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/RamonAlcantaraArceo/petstore-mcp)

Production-ready Python MCP server scaffold for the Petstore API.

## Quickstart

```bash
uv venv --seed --python 3.14 .venv
uv sync --all-extras
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run petstore-mcp
```

## Repository Structure

- `src/petstore_mcp/`: async MCP server, modular tools/resources, config, logging.
- `tests/petstore_mcp/`: mirrored tests for source modules.
- `.github/`: CI, release, docs workflows, templates, and Dependabot.
- `.vscode/`: development settings, tasks, and debugging profiles.
- `docs/` + `mkdocs.yml`: MkDocs Material documentation.

## Publishing

Release workflow publishes version tags (`v*.*.*`) to GitHub Packages using `uv publish` and the GitHub token.
