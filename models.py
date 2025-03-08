from sqlalchemy import Column, String, JSON, Numeric, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from database import Base

class Consignment(Base):
    __tablename__ = "consignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(SQLEnum('pending', 'verified', 'flagged', name='status_enum'))
    items = Column(JSON)
    destination = Column(String(100))
    customs_value = Column(Numeric)
    violations = Column(JSON)
    attachments = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class Rule(Base):
    __tablename__ = "rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    condition = Column(String)
    description = Column(String)
    status = Column(SQLEnum('active', 'inactive', name='rule_status_enum'))
    severity = Column(SQLEnum('high', 'medium', 'low', name='severity_enum')) 