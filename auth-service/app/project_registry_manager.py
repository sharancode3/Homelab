from collections.abc import Iterator
from typing import final

from app.project_registry import ProjectRegistryEntry
from app.storage.interfaces import ProjectRepository


@final
class DuplicateProjectIdError(ValueError):
    """Raised when a project ID is already registered."""


@final
class DuplicateProjectSlugError(ValueError):
    """Raised when a project slug is already registered."""


class ProjectRegistryManager:
    """Registry for platform projects backed by a persistent repository."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def register(self, project: ProjectRegistryEntry) -> None:
        """Register a project.

        Raises:
            DuplicateProjectIdError: If the project ID already exists.
            DuplicateProjectSlugError: If the project slug already exists.
        """
        if self._repository.get_by_project_id(project.project_id):
            raise DuplicateProjectIdError(
                f"Project ID already registered: {project.project_id}"
            )

        if self._repository.get_by_project_slug(project.project_slug):
            raise DuplicateProjectSlugError(
                f"Project slug already registered: {project.project_slug}"
            )

        self._repository.register(project)

    def get_by_project_id(self, project_id: str) -> ProjectRegistryEntry | None:
        """Return a project by its unique project ID."""
        return self._repository.get_by_project_id(project_id)

    def get_by_project_slug(self, project_slug: str) -> ProjectRegistryEntry | None:
        """Return a project by its canonical project slug."""
        return self._repository.get_by_project_slug(project_slug)

    @property
    def projects(self) -> tuple[ProjectRegistryEntry, ...]:
        """Return all registered projects as an immutable tuple."""
        return self._repository.get_all()

    def is_registered(self, project_id: str) -> bool:
        """Return whether a project ID is already registered."""
        return self.get_by_project_id(project_id) is not None

    def __len__(self) -> int:
        """Return the number of registered projects."""
        return len(self.projects)

    def __contains__(self, project_id: str) -> bool:
        """Return True when the given project ID is registered."""
        return self.is_registered(project_id)

    def __iter__(self) -> Iterator[ProjectRegistryEntry]:
        """Iterate over registered projects."""
        return iter(self.projects)