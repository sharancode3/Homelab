from dataclasses import dataclass, field

from app.security.permissions import Permission, Role, ROLE_PERMISSIONS


@dataclass(frozen=True, slots=True)
class IdentityContext:
    user_id: str
    roles: frozenset[Role] = field(default_factory=frozenset)
    _permissions: frozenset[Permission] | None = None

    @property
    def permissions(self) -> frozenset[Permission]:
        if self._permissions is not None:
            return self._permissions
            
        # Compute permissions from roles
        computed = set()
        for role in self.roles:
            computed.update(ROLE_PERMISSIONS.get(role, set()))
            
        return frozenset(computed)
