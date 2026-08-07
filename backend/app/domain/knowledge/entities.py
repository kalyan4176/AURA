from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
from uuid import UUID


class KnowledgeDocument(BaseModel):
    id: Optional[UUID] = None
    title: str
    content: str
    metadata_fields: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(from_attributes=True)


class BusinessRule(BaseModel):
    id: Optional[UUID] = None
    rule_name: str
    rule_condition: str
    business_impact: str

    model_config = ConfigDict(from_attributes=True)
