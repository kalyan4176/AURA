from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class Notification(BaseModel):
    id: Optional[UUID] = None
    type: str  # info, warning, error
    message: str
    is_read: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
