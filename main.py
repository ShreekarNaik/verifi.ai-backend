from fastapi import FastAPI, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from database import get_db, engine, Base
from models import Consignment, Rule
from schemas import (
    ConsignmentCreate, ConsignmentResponse, RuleCreate, RuleResponse,
    ComplianceCheck, ComplianceResponse, ConsignmentStatus, BatchComplianceCheck, BatchComplianceResponse,
    PaginatedConsignmentResponse
)
from rule_engine import ComplianceEngine

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Compliance Verification System")

# Consignment endpoints
@app.post("/api/v1/consignments", response_model=ConsignmentResponse)
def create_consignment(consignment: ConsignmentCreate, db: Session = Depends(get_db)):
    db_consignment = Consignment(
        status=ConsignmentStatus.PENDING,
        items=consignment.dict()["items"],
        destination=consignment.destination,
        customs_value=consignment.customs_value,
        attachments=consignment.attachments,
        violations=[]
    )
    db.add(db_consignment)
    db.commit()
    db.refresh(db_consignment)
    return db_consignment

@app.get("/api/v1/consignments/{consignment_id}", response_model=ConsignmentResponse)
def get_consignment(consignment_id: uuid.UUID, db: Session = Depends(get_db)):
    db_consignment = db.query(Consignment).filter(Consignment.id == consignment_id).first()
    if not db_consignment:
        raise HTTPException(status_code=404, detail="Consignment not found")
    return db_consignment

@app.put("/api/v1/consignments/{consignment_id}", response_model=ConsignmentResponse)
def update_consignment(
    consignment_id: uuid.UUID,
    consignment: ConsignmentCreate,
    db: Session = Depends(get_db)
):
    db_consignment = db.query(Consignment).filter(Consignment.id == consignment_id).first()
    if not db_consignment:
        raise HTTPException(status_code=404, detail="Consignment not found")
    
    update_data = consignment.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_consignment, field, value)
    
    db_consignment.status = ConsignmentStatus.PENDING
    db_consignment.violations = []
    
    db.commit()
    db.refresh(db_consignment)
    return db_consignment

@app.get("/api/v1/consignments", response_model=PaginatedConsignmentResponse)
def list_consignments(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    total = db.query(Consignment).count()
    consignments = db.query(Consignment)\
        .order_by(Consignment.created_at.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
    
    return {
        "consignments": consignments,
        "total": total,
        "skip": skip,
        "limit": limit
    }

# Rule endpoints
@app.post("/api/v1/rules", response_model=RuleResponse)
def create_rule(rule: RuleCreate, db: Session = Depends(get_db)):
    db_rule = Rule(**rule.dict())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@app.get("/api/v1/rules", response_model=List[RuleResponse])
def get_rules(db: Session = Depends(get_db)):
    return db.query(Rule).filter(Rule.status == 'active').all()

# Compliance check endpoint
@app.post("/api/v1/compliance/check", response_model=ComplianceResponse)
def check_compliance(check: ComplianceCheck, db: Session = Depends(get_db)):
    # Get consignment
    consignment = db.query(Consignment).filter(Consignment.id == check.consignment_id).first()
    if not consignment:
        raise HTTPException(status_code=404, detail="Consignment not found")

    # Get active rules
    active_rules = db.query(Rule).filter(Rule.status == 'active').all()
    
    # Create compliance engine and check rules
    engine = ComplianceEngine(active_rules)
    
    # Prepare consignment data for rule evaluation
    consignment_data = {
        "destination": consignment.destination,
        "customs_value": float(consignment.customs_value),
        "items": consignment.items,
    }
    
    # Check compliance
    status, violations = engine.check_compliance(consignment_data)
    
    # Update consignment with results
    consignment.status = status
    consignment.violations = [violation.dict() for violation in violations]
    db.commit()
    
    return ComplianceResponse(status=status, violations=violations)

# Report endpoint
@app.get("/api/v1/consignments/{consignment_id}/report")
def generate_report(consignment_id: uuid.UUID, db: Session = Depends(get_db)):
    consignment = db.query(Consignment).filter(Consignment.id == consignment_id).first()
    if not consignment:
        raise HTTPException(status_code=404, detail="Consignment not found")
    
    # For v1, return a simple JSON report
    return {
        "consignment_id": str(consignment.id),
        "status": consignment.status,
        "destination": consignment.destination,
        "customs_value": consignment.customs_value,
        "violations": consignment.violations,
        "created_at": consignment.created_at
    }

# Rule modification and deletion
@app.delete("/api/v1/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a specific rule"""
    rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    db.delete(rule)
    db.commit()
    return {"message": "Rule deleted successfully"}

@app.put("/api/v1/rules/{rule_id}", response_model=RuleResponse)
def update_rule(rule_id: uuid.UUID, rule: RuleCreate, db: Session = Depends(get_db)):
    """Update an existing rule"""
    db_rule = db.query(Rule).filter(Rule.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update rule fields
    for field, value in rule.dict().items():
        setattr(db_rule, field, value)
    
    db.commit()
    db.refresh(db_rule)
    return db_rule

# Consignment deletion
@app.delete("/api/v1/consignments/{consignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_consignment(consignment_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a specific consignment"""
    consignment = db.query(Consignment).filter(Consignment.id == consignment_id).first()
    if not consignment:
        raise HTTPException(status_code=404, detail="Consignment not found")
    
    db.delete(consignment)
    db.commit()
    return {"message": "Consignment deleted successfully"}


@app.post("/api/v1/compliance/batch-check", response_model=BatchComplianceResponse)
def batch_check_compliance(check: BatchComplianceCheck, db: Session = Depends(get_db)):
    """Check compliance for multiple consignments"""
    # Get active rules once for all checks
    active_rules = db.query(Rule).filter(Rule.status == 'active').all()
    engine = ComplianceEngine(active_rules)
    
    results = []
    verified_count = 0
    flagged_count = 0
    
    for consignment_id in check.consignment_ids:
        # Get consignment
        consignment = db.query(Consignment).filter(Consignment.id == consignment_id).first()
        if not consignment:
            continue  # Skip if consignment not found
        
        # Prepare consignment data
        consignment_data = {
            "destination": consignment.destination,
            "customs_value": float(consignment.customs_value),
            "items": consignment.items,
        }
        
        # Check compliance
        status, violations = engine.check_compliance(consignment_data)
        
        # Update consignment with results
        consignment.status = status
        consignment.violations = [violation.dict() for violation in violations]
        
        # Count results
        if status == ConsignmentStatus.VERIFIED:
            verified_count += 1
        else:
            flagged_count += 1
        
        results.append(ComplianceResponse(status=status, violations=violations))
    
    # Commit all changes
    db.commit()
    
    # Prepare summary
    summary = {
        "total_processed": len(results),
        "verified_count": verified_count,
        "flagged_count": flagged_count,
    }
    
    return BatchComplianceResponse(results=results, summary=summary) 