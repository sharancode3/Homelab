from dataclasses import dataclass
from datetime import datetime

@dataclass
class DeveloperUser:
    user_id: str
    username: str
    email: str
    hashed_password: str
    created_at: datetime
    is_active: bool = True
