from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID


class ReportComponent(BaseModel):
    id: str
    type: str  # chart, table, text
    title: str
    config: Dict[str, Any] = Field(default_factory=dict)
    annotations: List[str] = Field(default_factory=list)


class Comment(BaseModel):
    id: str
    user_email: str
    content: str
    created_at: datetime


class Report(BaseModel):
    id: Optional[UUID] = None
    workspace_id: UUID
    name: str
    components: List[ReportComponent] = Field(default_factory=list)
    layout: List[Dict[str, Any]] = Field(default_factory=list)
    comments: List[Comment] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
