import requests
import json
from datetime import datetime
import time

# Base URL for the API
BASE_URL = "http://localhost:8000/api/v1"

def print_response(response, endpoint):
    """Helper function to print response details"""
    print(f"\n=== Testing {endpoint} ===")
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))
    print("=" * 50)

def test_create_rules():
    """Test creating compliance rules"""
    rules = [
        {
            "name": "Restricted Countries Rule",
            "condition": "destination in ['Syria', 'North Korea', 'Iran']",
            "description": "Shipments to restricted countries are not allowed",
            "severity": "high",
            "status": "active"
        },
        {
            "name": "High Value Rule",
            "condition": "customs_value > 50000",
            "description": "High-value shipments require additional scrutiny",
            "severity": "medium",
            "status": "active"
        },
        {
            "name": "Restricted Items Rule",
            "condition": "any(item.get('requires_clearance', False) for item in items)",
            "description": "Items requiring clearance need special handling",
            "severity": "high",
            "status": "active"
        }
    ]
    
    created_rules = []
    for rule in rules:
        response = requests.post(f"{BASE_URL}/rules", json=rule)
        print_response(response, "CREATE RULE")
        if response.status_code == 200:
            created_rules.append(response.json())
    
    return created_rules

def test_get_rules():
    """Test getting all active rules"""
    response = requests.get(f"{BASE_URL}/rules")
    print_response(response, "GET RULES")
    return response.json()

def test_create_consignments():
    """Test creating consignments"""
    consignments = [
        {
            "items": [
                {
                    "name": "Medical Equipment",
                    "value": 75000,
                    "weight": 500,
                    "requires_clearance": True
                }
            ],
            "destination": "Iran",
            "customs_value": 75000,
            "attachments": ["invoice_001.pdf"]
        },
        {
            "items": [
                {
                    "name": "Office Supplies",
                    "value": 5000,
                    "weight": 100,
                    "requires_clearance": False
                }
            ],
            "destination": "Germany",
            "customs_value": 5000,
            "attachments": ["invoice_002.pdf"]
        },
        {
            "items": [
                {
                    "name": "Electronics",
                    "value": 60000,
                    "weight": 200,
                    "requires_clearance": True
                }
            ],
            "destination": "USA",
            "customs_value": 60000,
            "attachments": ["invoice_003.pdf"]
        }
    ]
    
    created_consignments = []
    for consignment in consignments:
        response = requests.post(f"{BASE_URL}/consignments", json=consignment)
        print_response(response, "CREATE CONSIGNMENT")
        if response.status_code == 200:
            created_consignments.append(response.json())
    
    return created_consignments

def test_get_consignment(consignment_id):
    """Test getting a specific consignment"""
    response = requests.get(f"{BASE_URL}/consignments/{consignment_id}")
    print_response(response, "GET CONSIGNMENT")
    return response.json()

def test_update_consignment(consignment_id):
    """Test updating a consignment"""
    update_data = {
        "items": [
            {
                "name": "Updated Medical Equipment",
                "value": 80000,
                "weight": 550,
                "requires_clearance": True
            }
        ],
        "destination": "France",
        "customs_value": 80000,
        "attachments": ["invoice_001_updated.pdf"]
    }
    
    response = requests.put(f"{BASE_URL}/consignments/{consignment_id}", json=update_data)
    print_response(response, "UPDATE CONSIGNMENT")
    return response.json()

def test_compliance_check(consignment_id):
    """Test compliance check for a consignment"""
    response = requests.post(
        f"{BASE_URL}/compliance/check",
        json={"consignment_id": consignment_id}
    )
    print_response(response, "COMPLIANCE CHECK")
    return response.json()

def test_generate_report(consignment_id):
    """Test report generation for a consignment"""
    response = requests.get(f"{BASE_URL}/consignments/{consignment_id}/report")
    print_response(response, "GENERATE REPORT")
    return response.json()

def main():
    """Main test execution function"""
    print("\nStarting API Tests...\n")
    
    # 1. Create and get rules
    print("\n=== Testing Rules API ===")
    created_rules = test_create_rules()
    all_rules = test_get_rules()
    
    # Wait a bit to ensure rules are properly saved
    time.sleep(1)
    
    # 2. Create consignments
    print("\n=== Testing Consignments API ===")
    created_consignments = test_create_consignments()
    
    if created_consignments:
        # Get the ID of the first consignment for further tests
        consignment_id = created_consignments[0]["id"]
        
        # 3. Test getting a specific consignment
        test_get_consignment(consignment_id)
        
        # 4. Test updating a consignment
        updated_consignment = test_update_consignment(consignment_id)
        
        # 5. Test compliance check
        compliance_result = test_compliance_check(consignment_id)
        
        # 6. Test report generation
        report = test_generate_report(consignment_id)
    
    print("\nAPI Tests Completed!")

if __name__ == "__main__":
    main() 