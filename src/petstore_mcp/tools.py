"""MCP tool registration and implementations."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any

from pydantic import BaseModel

from petstore_mcp.client import PetstoreClient
from petstore_mcp.schemas import (
    FindPetsByStatusInput,
    GetHealthInput,
    GetPetByIdInput,
    HealthOutput,
    PetOutput,
    PetsOutput,
)

LOGGER = logging.getLogger(__name__)

ToolFunction = Callable[["ToolContext", BaseModel], Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class ToolSpec:
    """Metadata for a tool registration entry.

    Attributes:
        name: Public tool name.
        description: Human-readable tool description.
        input_model: Pydantic input model.
        output_model: Pydantic output model.
        handler: Internal async implementation.
    """

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: ToolFunction


@dataclass(slots=True)
class ToolContext:
    """Dependencies used by tool handlers.

    Attributes:
        client: API client instance.
        timeout_seconds: Timeout for each tool execution.
    """

    client: PetstoreClient
    timeout_seconds: float


TOOL_REGISTRY: list[ToolSpec] = []


def mcp_tool(
    name: str,
    description: str,
    input_model: type[BaseModel],
    output_model: type[BaseModel],
) -> Callable[[ToolFunction], ToolFunction]:
    """Register a function as an MCP tool implementation.

    Args:
        name: Tool name exposed to MCP clients.
        description: Tool description.
        input_model: Input validation model.
        output_model: Output schema model.

    Returns:
        Decorator that registers tool metadata.
    """

    def decorator(func: ToolFunction) -> ToolFunction:
        TOOL_REGISTRY.append(
            ToolSpec(
                name=name,
                description=description,
                input_model=input_model,
                output_model=output_model,
                handler=func,
            )
        )

        @wraps(func)
        async def wrapped(context: ToolContext, payload: BaseModel) -> dict[str, Any]:
            """Execute wrapped tool handler.

            Args:
                context: Shared tool dependencies.
                payload: Validated tool payload.

            Returns:
                Tool response dictionary.
            """
            return await func(context, payload)

        return wrapped

    return decorator


@mcp_tool(
    name="health.check",
    description="Return Petstore service health data.",
    input_model=GetHealthInput,
    output_model=HealthOutput,
)
async def get_health_tool(context: ToolContext, payload: BaseModel) -> dict[str, Any]:
    """Return service health details.

    Args:
        context: Tool context with shared dependencies.
        payload: Input payload model.

    Returns:
        Health response payload.
    """
    del payload
    response = await context.client.get_health()
    return dict(response)


@mcp_tool(
    name="pet.find_by_status",
    description="Find pets filtered by status.",
    input_model=FindPetsByStatusInput,
    output_model=PetsOutput,
)
async def find_pets_by_status_tool(context: ToolContext, payload: BaseModel) -> dict[str, Any]:
    """Fetch pets by status.

    Args:
        context: Tool context with shared dependencies.
        payload: Input payload model.

    Returns:
        Pets list payload.
    """
    validated = FindPetsByStatusInput.model_validate(payload)
    items = await context.client.find_pets_by_status(validated.status.value)
    return {"items": [PetOutput.model_validate(item).model_dump() for item in items]}


@mcp_tool(
    name="pet.get_by_id",
    description="Get a pet by identifier.",
    input_model=GetPetByIdInput,
    output_model=PetOutput,
)
async def get_pet_by_id_tool(context: ToolContext, payload: BaseModel) -> dict[str, Any]:
    """Fetch one pet by id.

    Args:
        context: Tool context with shared dependencies.
        payload: Input payload model.

    Returns:
        One pet payload.
    """
    validated = GetPetByIdInput.model_validate(payload)
    item = await context.client.get_pet_by_id(validated.pet_id)
    return PetOutput.model_validate(item).model_dump()


def register_tools(app: Any, context: ToolContext) -> None:
    """Register all tool handlers into an MCP application.

    Args:
        app: MCP app instance exposing a `tool` decorator.
        context: Shared tool dependencies.

    Returns:
        None.
    """

    def build_handler(spec: ToolSpec) -> Callable[..., Awaitable[dict[str, Any]]]:
        """Create an isolated MCP handler for one tool spec.

        Args:
            spec: Tool metadata to bind.

        Returns:
            Async MCP handler function.
        """

        async def handler_factory(**kwargs: Any) -> dict[str, Any]:
            """Create execution wrapper around a registered tool.

            Args:
                kwargs: Runtime keyword arguments from MCP.

            Returns:
                Validated output payload.

            Raises:
                RuntimeError: If execution fails.
            """
            try:
                validated_input = spec.input_model.model_validate(kwargs)
                result = await asyncio.wait_for(
                    spec.handler(context, validated_input),
                    timeout=context.timeout_seconds,
                )
                validated_output = spec.output_model.model_validate(result)
                return validated_output.model_dump(mode="json")
            except TimeoutError as exc:
                LOGGER.exception("Tool timed out", extra={"tool": spec.name})
                raise RuntimeError(
                    f"Tool timed out after {context.timeout_seconds}s: {spec.name}"
                ) from exc
            except Exception as exc:
                LOGGER.exception("Tool failed", extra={"tool": spec.name})
                raise RuntimeError(f"Tool execution failed: {spec.name}: {exc!r}") from exc

        return handler_factory

    for spec in TOOL_REGISTRY:
        app.tool(name=spec.name, description=spec.description)(build_handler(spec))
