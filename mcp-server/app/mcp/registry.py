import importlib
import pkgutil
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.infrastructure.storage.s3_client import S3StorageClient
from app.repository.pets_repo import PetsRepository
import app.tools as tools_package


class MCPTool(Protocol):
    name: str


@dataclass(frozen=True)
class ToolDependencies:
    db: AsyncSession
    storage_client: S3StorageClient
    pets_repo: PetsRepository


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, MCPTool] = {}

    def register(self, tool: MCPTool) -> None:
        if not tool.name:
            raise ValidationAppError("Tool name cannot be empty")
        self._tools[tool.name] = tool

    def get(self, name: str) -> MCPTool:
        tool = self._tools.get(name)
        if tool is None:
            raise ValidationAppError(f"Tool '{name}' is not registered")
        return tool

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())


def build_tool_registry(db: AsyncSession) -> ToolRegistry:
    registry = ToolRegistry()
    dependencies = ToolDependencies(
        db=db,
        storage_client=S3StorageClient(),
        pets_repo=PetsRepository(db),
    )

    for module_info in pkgutil.iter_modules(tools_package.__path__):
        module_name = f"{tools_package.__name__}.{module_info.name}.tool"
        module = importlib.import_module(module_name)
        factory = getattr(module, "create_tool", None)
        if factory is None or not callable(factory):
            continue
        registry.register(factory(dependencies))

    return registry
