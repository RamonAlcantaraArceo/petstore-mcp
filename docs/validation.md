# Validate the Petstore MCP server

This page explains how to start the Petstore MCP server, run quick smoke checks, and use the included validation script to confirm the MCP tooling can reach your Petstore API.

## Prerequisites

- Python 3.14 (project uses `pyproject.toml` and `uv` helper tooling)
- Project dependencies installed in a virtual environment (see Quickstart in the repository README)

Quick setup (already used in CI):

```bash
uv venv --seed --python 3.14 .venv
uv sync --all-extras
uv run ruff check .
uv run pytest
```

## Environment variables

The MCP server reads runtime settings from environment variables with the `PETSTORE_MCP_` prefix. Useful variables:

- `PETSTORE_MCP_API_BASE_URL` — Petstore API base URL. Default: `https://petstore-api-dev.ramon-alcantara.work`.
- `PETSTORE_MCP_API_KEY` — Optional API key sent as `X-API-Key`.
- `PETSTORE_MCP_REQUEST_TIMEOUT_SECONDS` — Per-request timeout (float).

You can set them in your shell or add them to a `.env` file at the repo root.

## Start the Petstore API (if running locally)

Run whatever local dev server you use for the Petstore API. For example, if you have a local dev Petstore on port `8080`:

```bash
# in one terminal: start your Petstore API
# (this depends on your Petstore project)
```

## Start the MCP server

Start the MCP server with the environment variables pointing to your Petstore service:

```bash
export PETSTORE_MCP_API_BASE_URL="http://localhost:8080"
export PETSTORE_MCP_API_KEY="your-api-key"
uv run petstore-mcp
```

You should see a log line similar to `Petstore MCP application initialized` when the MCP app boots.

## Quick manual smoke checks (Petstore API)

Use `curl` or `http` to verify the Petstore API itself first:

```bash
curl -sS "$PETSTORE_MCP_API_BASE_URL/health" | jq .
curl -sS "$PETSTORE_MCP_API_BASE_URL/api/v1/pet/findByStatus?status=available" | jq '.[0]'
curl -sS "$PETSTORE_MCP_API_BASE_URL/api/v1/pet/1" | jq .
```

If those succeed, the Petstore API is reachable and returning JSON.

## Validation script (automated checks)

This repository includes `scripts/validate_mcp.py`. The script performs two checks:

1. Calls the Petstore API `/health` endpoint using the same `PetstoreClient` the MCP uses.
2. Registers the MCP tool handlers into a small local stub app and invokes the `health.check`, `pet.find_by_status`, and `pet.get_by_id` handlers. That proves the tools are wired correctly and the handlers can call the remote Petstore API.

Run the script like this:

```bash
# use uv to ensure the repository virtual environment is used
uv run python scripts/validate_mcp.py

# or pass explicit args
python scripts/validate_mcp.py --api-base-url http://localhost:8080 --api-key yourkey --timeout 5
```

Expected script output shows the Petstore health payload and the results from the three tool invocations. Errors indicate network or schema problems.

## Manual MCP (server) endpoint testing

The `scripts/validate_mcp.py` validates the tooling and API connectivity; it does not exercise the MCP server's network API surface. To test the MCP server process itself:

1. Start the MCP server (`uv run petstore-mcp`).
2. Watch server logs for `Petstore MCP application initialized` and any error traces.
3. If your FastMCP deployment exposes an HTTP bridge or JSON-RPC, use the tool/resource URL exposed by your FastMCP configuration to call `health.check`, `pet.find_by_status`, or `pet.get_by_id` from `curl` or your MCP client.

If you want, I can add a small HTTP client that calls the live MCP server endpoints — tell me the HTTP paths your FastMCP instance exposes (or I can attempt to discover them).

## Troubleshooting

- `Connection refused` or timeout: verify the Petstore API base URL and that the service is running. Check `PETSTORE_MCP_API_BASE_URL` for typos.
- `HTTP 4xx/5xx`: inspect the Petstore API logs and the MCP server logs. The validation script prints exception details when calls fail.
- Schema validation errors: the tools validate inputs/outputs with Pydantic models. A schema mismatch indicates the API returned unexpected data.

---

If you'd like, I can also add a small test that starts the MCP server in a subprocess and exercises the HTTP endpoints directly; tell me if you want that automated E2E check added here.
