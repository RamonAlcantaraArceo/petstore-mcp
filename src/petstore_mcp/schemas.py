"""Schema definitions for MCP tools and resources."""

from enum import StrEnum

from pydantic import BaseModel, Field


class PetStatus(StrEnum):
    """Allowed Petstore pet statuses."""

    AVAILABLE = "available"
    PENDING = "pending"
    SOLD = "sold"


class GetHealthInput(BaseModel):
    """Input schema for health tool.

    Attributes:
        include_details: Whether metadata details are requested.
    """

    include_details: bool = Field(default=True)


class HealthDetails(BaseModel):
    """Health details schema.

    Attributes:
        version: Current application version.
        build_date: Build date value.
        git_commit_sha: Git commit SHA.
    """

    version: str
    build_date: str
    git_commit_sha: str


class HealthOutput(BaseModel):
    """Output schema for health responses.

    Attributes:
        status: Service status.
        mode: Runtime mode.
        details: Optional service metadata.
    """

    status: str
    mode: str
    details: HealthDetails | None = None


class FindPetsByStatusInput(BaseModel):
    """Input schema for listing pets by status.

    Attributes:
        status: Pet status filter.
    """

    status: PetStatus = Field(default=PetStatus.AVAILABLE)


class PetOutput(BaseModel):
    """Output schema for pet entities.

    Attributes:
        id: Pet identifier.
        name: Pet name.
        status: Optional Petstore status.
    """

    id: int | None = None
    name: str
    status: PetStatus | None = None


class PetsOutput(BaseModel):
    """Output schema for a list of pets.

    Attributes:
        items: Pet collection.
    """

    items: list[PetOutput]


class GetPetByIdInput(BaseModel):
    """Input schema for fetching one pet.

    Attributes:
        pet_id: Pet identifier.
    """

    pet_id: int = Field(gt=0)
