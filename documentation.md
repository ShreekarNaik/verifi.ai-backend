# Compliance Verification System Backend Documentation (Version 1.0)  
**Focus**: Core compliance logic, data ingestion, and basic reporting. Authentication/UI integration deferred to v2.0.  

---

## 1. Data Models  
### **Consignment**  
```json  
{  
  "id": "uuid",  
  "status": "pending | verified | flagged",  
  "items": [  
    {  
      "name": "string",  
      "value": "number",  
      "weight": "number",  
      "requires_clearance": "boolean"  
    }  
  ],  
  "destination": "string",  
  "customs_value": "number",  
  "violations": [  
    {  
      "rule_id": "string",  
      "description": "string",  
      "resolution_steps": "string",  
      "condition_str": "string"  
    }  
  ],  
  "attachments": ["string"],  
  "created_at": "timestamp"  
}  
```  

### **Rule**  
```json  
{  
  "id": "uuid",  
  "name": "string",  
  "condition": "string",  // e.g., "destination in ['Syria', 'North Korea'] and customs_value > 10000"  
  "description": "string",  
  "status": "active | inactive",  
  "severity": "high | medium | low"  
}  
```  

---

## 2. API Endpoints  

### **Consignment Management**  
| Method | Endpoint                  | Description                                                                 |  
|--------|---------------------------|-----------------------------------------------------------------------------|  
| POST   | `/api/v1/consignments`    | Create a single consignment (manual entry).                                |  
| POST   | `/api/v1/consignments/batch` | Upload CSV for batch creation (returns preview data).                     |  
| POST   | `/api/v1/consignments/preview` | Preview CSV-parsed consignments before committing to DB.                |  
| GET    | `/api/v1/consignments/{id}` | Retrieve consignment details with compliance status.                     |  
| PUT    | `/api/v1/consignments/{id}` | Update consignment (used for "Edit and Recheck" feature).                |  

**Example Request (Single Consignment)**:  
```json  
{  
  "items": [{"name": "Medical Device", "value": 15000, "weight": 200, "requires_clearance": true}],  
  "destination": "Iran",  
  "customs_value": 45000,  
  "attachments": ["invoice.pdf"]  
}  
```  

---

### **Rule Management**  
| Method | Endpoint          | Description                              |  
|--------|-------------------|------------------------------------------|  
| GET    | `/api/v1/rules`   | List active rules (used by compliance engine). |  
| POST   | `/api/v1/rules`   | Add new rules (static for v1.0).         |  

**Example Rule Response**:  
```json  
{  
  "active_rules": [  
    {  
      "id": "rule_sanctioned_countries",  
      "condition": "destination in ['Syria', 'North Korea']",  
      "description": "Block shipments to sanctioned countries"  
    }  
  ]  
}  
```  

---

### **Compliance Engine**  
| Method | Endpoint                          | Description                                      |  
|--------|-----------------------------------|--------------------------------------------------|  
| POST   | `/api/v1/compliance/check`        | Check consignment against **all active rules**.  |  

**Request**:  
```json  
{  
  "consignment_id": "uuid"  
}  
```  

**Response**:  
```json  
{  
  "status": "flagged",  
  "violations": [  
    {  
      "rule_id": "rule_sanctioned_countries",  
      "condition_str": "destination in ['Syria', 'North Korea']",  
      "actual_value": "Iran"  
    }  
  ]  
}  
```  

---

### **Reporting**  
| Method | Endpoint                              | Description                                      |  
|--------|---------------------------------------|--------------------------------------------------|  
| GET    | `/api/v1/consignments/{id}/report`    | Generate basic compliance report (PDF/HTML).     |  

**Response**:  
```json  
{  
  "report_url": "/reports/consignment_123.pdf"  // Pre-signed URL or static path  
}  
```  

---

## 3. Database Schema (PostgreSQL)  
### **consignments**  
| Column         | Type          | Details                                  |  
|----------------|---------------|------------------------------------------|  
| id             | UUID          | Primary Key                              |  
| status         | VARCHAR(20)   | ENUM: pending, verified, flagged         |  
| items          | JSONB         | Array of item objects                    |  
| destination    | VARCHAR(100)  |                                          |  
| customs_value  | NUMERIC       |                                          |  
| violations     | JSONB         | Array of violation objects               |  
| attachments    | JSONB         | Array of file URLs                       |  
| created_at     | TIMESTAMP     | DEFAULT NOW()                            |  

### **rules**  
| Column         | Type          | Details                                  |  
|----------------|---------------|------------------------------------------|  
| id             | UUID          | Primary Key                              |  
| name           | VARCHAR(100)  |                                          |  
| condition      | TEXT          | Rule string (e.g., "customs_value > 10000") |  
| description    | TEXT          |                                          |  
| status         | VARCHAR(20)   | ENUM: active, inactive                   |  
| severity       | VARCHAR(20)   | ENUM: high, medium, low                  |  

---

## 4. Rule Checker Workflow  
1. **Input**: Consignment ID is sent to `/api/v1/compliance/check`.  
2. **Fetch Data**: Retrieve consignment and active rules from DB.  
3. **Evaluate**:  
   - Use `RuleParser` to break rules into conditions.  
   - Use `RuleEvaluator` to check each condition against consignment data.  
4. **Output**: Return compliance status and detailed violations.  

---

## 5. Versioning Strategy  
- **URL Versioning**: `/api/v1/...`  
- **Backward Compatibility**:  
  - New fields in v2.0+ will be optional.  
  - Breaking changes (e.g., schema updates) will increment the version.  

