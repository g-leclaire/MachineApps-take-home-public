import logging
import os

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel
from storage.accessor import ModelAccessor
from storage.bootstrap import bootstrap

from validation import validate_coordinates

CONFIG_ID = 1
DEFAULT_DATABASE_URL = "sqlite:///./gantry.db"

logger = logging.getLogger(__name__)


class GantryConfig(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cube_position: list[float] = Field(sa_column=Column(JSON, nullable=False))
    destination_position: list[float] = Field(sa_column=Column(JSON, nullable=False))


def init_storage() -> ModelAccessor[GantryConfig]:
    bootstrap(database_url=os.getenv("GANTRY_DATABASE_URL", DEFAULT_DATABASE_URL), auto_migrate=True)
    return ModelAccessor(GantryConfig, "gantry_config")


def load_target_positions(accessor: ModelAccessor[GantryConfig]) -> tuple[list[float], list[float]] | None:
    config = accessor.get(CONFIG_ID)
    if config is None:
        return None
    try:
        return (
            validate_coordinates(list(config.cube_position)),
            validate_coordinates(list(config.destination_position)),
        )
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid stored target positions", exc_info=True)
        return None


def save_target_positions(
    accessor: ModelAccessor[GantryConfig], cube_position: list[float], destination_position: list[float]
) -> None:
    accessor.save(
        GantryConfig(
            id=CONFIG_ID,
            cube_position=validate_coordinates(list(cube_position)),
            destination_position=validate_coordinates(list(destination_position)),
        )
    )
