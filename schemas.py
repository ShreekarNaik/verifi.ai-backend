from pydantic import BaseModel, UUID4
from typing import List, Optional
from datetime import datetime
from enum import Enum

class ConsignmentStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FLAGGED = "flagged"

class RuleStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Item(BaseModel):
    name: str
    value: float
    weight: float
    requires_clearance: bool

class Violation(BaseModel):
    rule_id: str
    description: str
    resolution_steps: Optional[str] = None
    condition_str: str

class ConsignmentBase(BaseModel):
    items: List[Item]
    destination: str
    customs_value: float
    attachments: List[str] = []

class ConsignmentCreate(ConsignmentBase):
    pass

class ConsignmentResponse(ConsignmentBase):
    id: UUID4
    status: ConsignmentStatus
    violations: List[Violation] = []
    created_at: datetime

    class Config:
        from_attributes = True

class RuleBase(BaseModel):
    name: str
    condition: str
    description: str
    severity: Severity
    status: RuleStatus = RuleStatus.ACTIVE

class RuleCreate(RuleBase):
    pass

class RuleResponse(RuleBase):
    id: UUID4

    class Config:
        from_attributes = True

class ComplianceCheck(BaseModel):
    consignment_id: UUID4

class ComplianceResponse(BaseModel):
    status: ConsignmentStatus
    violations: List[Violation] 