# Validate the Petstore MCP server

This page explains how to start the Petstore MCP server, run quick smoke checks, and use the included validation script to confirm the MCP tooling can reach your Petstore API.

## Fast path (recommended)

If you want to quickly confirm that everything works, do these steps:

1. Run `uv run pytest`.
2. Run `uv run python scripts/validate_mcp.py`.
3. Start the MCP server with `uv run petstore-mcp`.
4. Confirm logs include `Petstore MCP application initialized`.

This validates both code-level behavior (tests + tool wiring) and runtime startup (server process boots).

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
- `PETSTORE_MCP_LOG_LEVEL` — Set to `DEBUG` to print the resolved API base URL and outbound request URLs.

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

## What success looks like

- `uv run pytest` ends with all tests passing.
- `uv run python scripts/validate_mcp.py` ends with `All checks passed.`.
- `uv run petstore-mcp` starts without traceback and logs `Petstore MCP application initialized`.
- With `PETSTORE_MCP_LOG_LEVEL=DEBUG`, startup logs include `Resolved Petstore API configuration: base_url=...`.

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
2. Registers the MCP tool handlers into a small local stub app and invokes the `health_check`, `pet_find_by_status`, and `pet_get_by_id` handlers. That proves the tools are wired correctly and the handlers can call the remote Petstore API.

Important: this script validates MCP tool wiring and API connectivity, but it does not call the MCP server over a network protocol.

Important: `/health` may be public while `/api/v1/pet/*` can require `PETSTORE_MCP_API_KEY`. If `pet_find_by_status` or `pet_get_by_id` returns `401 Unauthorized`, set a valid API key.

Run the script like this:

```bash
# use uv to ensure the repository virtual environment is used
uv run python scripts/validate_mcp.py

# or pass explicit args
python scripts/validate_mcp.py --api-base-url http://localhost:8080 --api-key yourkey --timeout 5
```

Expected script output shows the Petstore health payload and the results from the three tool invocations. Errors indicate network or schema problems.

## Validate the running server process

To validate the running MCP server process itself:

1. Start the server in one terminal with `uv run petstore-mcp`.
2. Keep that terminal open and confirm the startup log appears.
3. In a second terminal, run `uv run python scripts/validate_mcp.py` to verify the same runtime dependencies can reach the Petstore API and execute MCP tool logic.

This gives you practical confidence that the deployed process and tool layer are working together in your current environment.

## Interact with the MCP server over MCP

If you want a real MCP client to talk to the server, use `scripts/call_mcp_server.py`. Unlike `scripts/validate_mcp.py`, this script starts the MCP server as a subprocess and communicates with it over MCP stdio.

List the exposed tools and resources:

```bash
uv run python scripts/call_mcp_server.py --list
```

Call the health tool over MCP:

```bash
uv run python scripts/call_mcp_server.py \
	--tool health_check \
	--arguments '{"include_details": true}'
```

Call the pet search tool over MCP:

```bash
uv run python scripts/call_mcp_server.py \
	--tool pet_find_by_status \
	--arguments '{"status": "available"}'
```

Call the pet lookup tool over MCP:

```bash
uv run python scripts/call_mcp_server.py \
	--tool pet_get_by_id \
	--arguments '{"pet_id": 1}'
```

The child server process inherits your shell environment, so set `PETSTORE_MCP_API_BASE_URL`, `PETSTORE_MCP_API_KEY`, and `PETSTORE_MCP_LOG_LEVEL` before running the script when needed.

## Prompt-driven agent example

If you want a minimal agent loop instead of specifying the tool yourself, use `scripts/agent_with_mcp.py`. It applies simple prompt routing rules, chooses a tool, and then calls the MCP server over stdio.

Check service health:

```bash
uv run python scripts/agent_with_mcp.py "is the petstore service healthy?"
```

Get a pet by id:

```bash
uv run python scripts/agent_with_mcp.py "get pet 1"
```

Find available pets:

```bash
uv run python scripts/agent_with_mcp.py "show me available pets"
```

This is intentionally small and deterministic. It is useful for smoke testing an agent-style interaction path without adding an LLM dependency.

## LLM-backed agent path with Docker Compose

If you want an LLM in the loop, this repo includes `docker-compose.llm.yml` (Ollama + Open WebUI) and `scripts/llm_agent_with_mcp.py`.

1. Start the local LLM services:

```bash
docker compose -f docker-compose.llm.yml up -d ollama open-webui
docker compose -f docker-compose.llm.yml run --rm ollama-pull
```

2. Optional: open the local chat UI at `http://localhost:3000`.

3. Run the LLM-backed MCP agent example:

```bash
export PETSTORE_MCP_API_BASE_URL="http://localhost:8000"
export PETSTORE_MCP_API_KEY="your-api-key"

uv run python scripts/llm_agent_with_mcp.py "show me available pets"
uv run python scripts/llm_agent_with_mcp.py "is the petstore service healthy?"
uv run python scripts/llm_agent_with_mcp.py "get pet 1"
```

The script asks Ollama to choose a tool and arguments, then calls `petstore-mcp` over MCP stdio.

Notes:

- Default LLM endpoint is `http://localhost:11434` (`OLLAMA_BASE_URL`).
- Default model is `llama3.2:3b` (`OLLAMA_MODEL`).
- If Ollama is unavailable or returns invalid JSON, the script falls back to deterministic routing.

## Independent MCP server mode (no subprocess spawn)

By default, `petstore-mcp` runs on stdio. To run it as an independent network service, use streamable HTTP transport.

Run in a terminal:

```bash
export PETSTORE_MCP_TRANSPORT="streamable-http"
export PETSTORE_MCP_HOST="127.0.0.1"
export PETSTORE_MCP_PORT="8765"
export PETSTORE_MCP_MOUNT_PATH="/"

export PETSTORE_MCP_API_BASE_URL="http://localhost:8000"
export PETSTORE_MCP_API_KEY="your-api-key"
export PETSTORE_MCP_LOG_LEVEL="DEBUG"

uv run petstore-mcp
```

This exposes the MCP endpoint at `http://127.0.0.1:8765/mcp`.

Use the independent LLM-backed client (does not spawn the MCP server):

```bash
docker compose -f docker-compose.llm.yml up -d ollama
docker compose -f docker-compose.llm.yml run --rm ollama-pull

uv run python scripts/llm_agent_with_running_mcp.py \
	--mcp-url http://127.0.0.1:8765/mcp \
	"show me available pets"
```

## VS Code MCP setup (stdio and independent HTTP)

The repository includes `.vscode/mcp.json` with two server entries:

- `petstore-mcp-stdio`: VS Code starts `uv run petstore-mcp` for you (stdio mode).
- `petstore-mcp-http`: VS Code connects to `http://127.0.0.1:8765/mcp` (server runs independently).

### Option A: VS Code-managed stdio server

1. Open this workspace in VS Code.
2. Ensure `.vscode/mcp.json` has valid `PETSTORE_MCP_API_BASE_URL` and `PETSTORE_MCP_API_KEY` values.
3. In Copilot Chat, select/use the `petstore-mcp-stdio` server.
4. Ask: `show me available pets`.

### Option B: Independently running server (normal or debugger)

1. Start the server yourself in one terminal (commands above), or run the debugger profile:
	 `Debug MCP server (streamable-http)` from `.vscode/launch.json`.
2. In Copilot Chat, select/use the `petstore-mcp-http` server.
3. Ask: `show me available pets`.

In both options, the request goes through MCP tools into your Petstore service.

## Register in a local MCP host

To expose this server to an external MCP-capable agent or desktop host, register it as a stdio server.

Use these command values:

- Command: `uv`
- Args: `run`, `petstore-mcp`
- Working directory: the repository root
- Environment: `PETSTORE_MCP_API_BASE_URL`, `PETSTORE_MCP_API_KEY`, and optionally `PETSTORE_MCP_LOG_LEVEL`

Generic stdio host configuration example:

```json
{
	"servers": {
		"petstore-mcp": {
			"command": "uv",
			"args": ["run", "petstore-mcp"],
			"cwd": "/absolute/path/to/petstore-mcp",
			"env": {
				"PETSTORE_MCP_API_BASE_URL": "http://localhost:8000",
				"PETSTORE_MCP_API_KEY": "your-api-key",
				"PETSTORE_MCP_LOG_LEVEL": "INFO"
			}
		}
	}
}
```

If your host uses a UI instead of JSON, enter the same command, args, working directory, and environment values there. Once registered, the external agent should see the same three tools: `health_check`, `pet_find_by_status`, and `pet_get_by_id`.

## Troubleshooting

- `Connection refused` or timeout: verify the Petstore API base URL and that the service is running. Check `PETSTORE_MCP_API_BASE_URL` for typos.
- `HTTP 4xx/5xx`: inspect the Petstore API logs and the MCP server logs. The validation script prints exception details when calls fail.
- Schema validation errors: the tools validate inputs/outputs with Pydantic models. A schema mismatch indicates the API returned unexpected data.

---

If you need strict protocol-level validation next, add an MCP client integration test that launches `petstore-mcp` in a subprocess and sends real MCP requests over the configured transport.
