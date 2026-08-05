from collections.abc import Iterator
from typing import final

from app.project_registry import ProjectRegistryEntry


@final
class DuplicateProjectIdError(ValueError):
    """Raised when a project ID is already registered."""


@final
class DuplicateProjectSlugError(ValueError):
    """Raised when a project slug is already registered."""


class ProjectRegistryManager:
    """In-memory registry for platform projects.

    The projects property and iteration both preserve registration order.
    """

    def __init__(self) -> None:
        self._projects_by_id: dict[str, ProjectRegistryEntry] = {}
        self._projects_by_slug: dict[str, ProjectRegistryEntry] = {}

    def register(self, project: ProjectRegistryEntry) -> None:
        """Register a project.

        Raises:
            DuplicateProjectIdError: If the project ID already exists.
            DuplicateProjectSlugError: If the project slug already exists.
        """
        if project.project_id in self._projects_by_id:
            raise DuplicateProjectIdError(
                f"Project ID already registered: {project.project_id}"
            )

        if project.project_slug in self._projects_by_slug:
            raise DuplicateProjectSlugError(
                f"Project slug already registered: {project.project_slug}"
            )

        self._projects_by_id[project.project_id] = project
        self._projects_by_slug[project.project_slug] = project

    def get_by_project_id(self, project_id: str) -> ProjectRegistryEntry | None:
        """Return a project by its unique project ID."""
        return self._projects_by_id.get(project_id)

    def get_by_project_slug(self, project_slug: str) -> ProjectRegistryEntry | None:
        """Return a project by its canonical project slug."""
        return self._projects_by_slug.get(project_slug)

    @property
    def projects(self) -> tuple[ProjectRegistryEntry, ...]:
        """Return all registered projects as an immutable tuple."""
        return tuple(self._projects_by_id.values())

    def is_registered(self, project_id: str) -> bool:
        """Return whether a project ID is already registered."""
        return project_id in self._projects_by_id

    def __len__(self) -> int:
        """Return the number of registered projects."""
        return len(self._projects_by_id)

    def __contains__(self, project_id: str) -> bool:
        """Return True when the given project ID is registered.

        Membership checks are ID-based only.
        """
        return project_id in self._projects_by_id

    def __iter__(self) -> Iterator[ProjectRegistryEntry]:
        """Iterate over registered projects in registration order."""
        return iter(self._projects_by_id.values())