from dataclasses import dataclass
from datetime import datetime

from app.platform.lifecycle.enums import LifecycleOperation, LifecycleState


@dataclass(frozen=True, slots=True)
class LifecycleResult:
    project_id: str
    project_slug: str
    project_name: str
    operation: LifecycleOperation
    previous_state: LifecycleState | None
    current_state: LifecycleState
    success: bool
    changed: bool
    message: str
    timestamp: datetime
