#!/usr/bin/env python3
"""
Synthetic Data Generator for AI Credit-Risk Investigation Agent
Project: TAG Ecosystem AI Engineering Bootcamp - Project 3 (Team Navigators)

Generates:
1. applications.csv & applications.json (Credit application profiles)
2. transactions.csv & transactions.json (90-day bank transaction histories linked by applicant_id)
3. golden_demo_cases.json (Curated test personas explicitly matching policy rules)
"""

import os
import csv
import json
import random
import math
from datetime import datetime, date, timedelta

# Output directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")
TEST_CASES_DIR = os.path.join(DATA_DIR, "test_cases")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(TEST_CASES_DIR, exist_ok=True)

# Set seed for reproducible synthetic generation
random.seed(42)

# Helper: Loan Payment Amortization Formula
def calculate_monthly_payment(principal, annual_rate_pct, term_months):
    if term_months <= 0:
        return 0.0
    monthly_rate = (annual_rate_pct / 100.0) / 12.0
    if monthly_rate == 0:
        return round(principal / term_months, 2)
    pmt = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
    return round(pmt, 2)

# --- Curated Golden Personas ---
GOLDEN_PERSONAS = [
    {
        "applicant_id": "CUST-GOLD-001",
        "application_id": "APP-2026-001",
        "full_name": "Sarah Jenkins",
        "age": 34,
        "email": "sarah.jenkins@example.com",
        "phone": "+1-555-0101",
        "address": "742 Evergreen Terrace, Springfield, IL",
        "housing_status": "MORTGAGE",
        "employment_status": "EMPLOYED_FULL_TIME",
        "employer_name": "Apex Healthcare Systems",
        "job_title": "Senior Clinical Analyst",
        "employment_length_months": 48,
        "declared_annual_income": 78000.0,
        "declared_monthly_net_income": 5000.0,
        "actual_monthly_salary": 5000.0,  # Matches application exactly
        "credit_score": 760,
        "credit_score_tier": "TIER_1_PRIME",
        "requested_loan_amount": 15000.0,
        "loan_purpose": "HOME_IMPROVEMENT",
        "loan_term_months": 36,
        "interest_rate_pct": 7.5,
        "declared_existing_monthly_debt": 450.0,
        "declared_monthly_housing_expense": 1400.0,
        "dependents_count": 1,
        "bankruptcies_count": 0,
        "tax_liens_count": 0,
        "persona_type": "GOLDEN_PRIME_APPROVAL",
        "expected_verdict": "ELIGIBLE_FOR_APPROVAL",
        "notes": "Low DTI (24.5%), stable income, perfect savings buffer, zero transaction red flags. Clean prime borrower."
    },
    {
        "applicant_id": "CUST-GOLD-002",
        "application_id": "APP-2026-002",
        "full_name": "Marcus Vance",
        "age": 29,
        "email": "marcus.vance@example.com",
        "phone": "+1-555-0102",
        "address": "1204 Pine Hollow Road, Austin, TX",
        "housing_status": "RENT",
        "employment_status": "EMPLOYED_FULL_TIME",
        "employer_name": "TechCorp Logistics",
        "job_title": "Operations Coordinator",
        "employment_length_months": 14,
        "declared_annual_income": 90000.0,
        "declared_monthly_net_income": 7500.0,
        "actual_monthly_salary": 3200.0,  # 57% lower than declared! Breaches POL-INC-001
        "credit_score": 690,
        "credit_score_tier": "TIER_2_NEAR_PRIME",
        "requested_loan_amount": 25000.0,
        "loan_purpose": "DEBT_CONSOLIDATION",
        "loan_term_months": 48,
        "interest_rate_pct": 9.5,
        "declared_existing_monthly_debt": 600.0,
        "declared_monthly_housing_expense": 1250.0,
        "dependents_count": 0,
        "bankruptcies_count": 0,
        "tax_liens_count": 0,
        "persona_type": "GOLDEN_INCOME_DISCREPANCY",
        "expected_verdict": "FURTHER_REVIEW_REQUIRED",
        "notes": "Severe income falsification (>57% variance). Also received a suspicious $15,000 window dressing deposit prior to applying."
    },
    {
        "applicant_id": "CUST-GOLD-003",
        "application_id": "APP-2026-003",
        "full_name": "Chloe Bennett",
        "age": 27,
        "email": "chloe.b@example.com",
        "phone": "+1-555-0103",
        "address": "45 Oak Ridge Boulevard, Denver, CO",
        "housing_status": "RENT",
        "employment_status": "EMPLOYED_FULL_TIME",
        "employer_name": "Mile High Marketing",
        "job_title": "Digital Media Specialist",
        "employment_length_months": 22,
        "declared_annual_income": 50400.0,
        "declared_monthly_net_income": 3500.0,
        "actual_monthly_salary": 3500.0,
        "credit_score": 655,
        "credit_score_tier": "TIER_3_SUBPRIME",
        "requested_loan_amount": 10000.0,
        "loan_purpose": "MAJOR_PURCHASE",
        "loan_term_months": 36,
        "interest_rate_pct": 12.0,
        "declared_existing_monthly_debt": 350.0,
        "declared_monthly_housing_expense": 1100.0,
        "dependents_count": 0,
        "bankruptcies_count": 0,
        "tax_liens_count": 0,
        "persona_type": "GOLDEN_GAMBLING_NSF",
        "expected_verdict": "DECLINE_RECOMMENDED",
        "notes": "Heavy gambling spend (>35% of monthly income), 4 NSF overdraft fees in 90 days. Rapid balance exhaustion before payday."
    },
    {
        "applicant_id": "CUST-GOLD-004",
        "application_id": "APP-2026-004",
        "full_name": "David O'Connor",
        "age": 42,
        "email": "david.oconnor@example.com",
        "phone": "+1-555-0104",
        "address": "88 Elmwood Avenue, Columbus, OH",
        "housing_status": "MORTGAGE",
        "employment_status": "EMPLOYED_FULL_TIME",
        "employer_name": "Midwest Industrial Supply",
        "job_title": "Supply Chain Supervisor",
        "employment_length_months": 60,
        "declared_annual_income": 62400.0,
        "declared_monthly_net_income": 4200.0,
        "actual_monthly_salary": 4200.0,
        "credit_score": 685,
        "credit_score_tier": "TIER_2_NEAR_PRIME",
        "requested_loan_amount": 18000.0,
        "loan_purpose": "DEBT_CONSOLIDATION",
        "loan_term_months": 48,
        "interest_rate_pct": 10.2,
        "declared_existing_monthly_debt": 350.0,  # Declared car payment only
        "declared_monthly_housing_expense": 1300.0,
        "dependents_count": 2,
        "bankruptcies_count": 0,
        "tax_liens_count": 0,
        "persona_type": "GOLDEN_UNDISCLOSED_DEBT",
        "expected_verdict": "FURTHER_REVIEW_REQUIRED",
        "notes": "Stated DTI is 23.4%, but bank statements reveal $740/mo in undisclosed BNPL & micro-loan debits. True Shadow DTI is 48.2%."
    },
    {
        "applicant_id": "CUST-GOLD-005",
        "application_id": "APP-2026-005",
        "full_name": "Elena Rostova",
        "age": 23,
        "email": "elena.rostova@example.com",
        "phone": "+1-555-0105",
        "address": "312 Beacon Street, Boston, MA",
        "housing_status": "RENT",
        "employment_status": "PART_TIME",
        "employer_name": "QuickServe Dining",
        "job_title": "Crew Member",
        "employment_length_months": 4,
        "declared_annual_income": 20400.0,
        "declared_monthly_net_income": 1500.0,  # Below $2,000 threshold (Rule POL-ELG-002)
        "actual_monthly_salary": 1500.0,
        "credit_score": 540,  # Below 600 Knockout (Rule POL-SCR-001)
        "credit_score_tier": "TIER_4_HIGH_RISK",
        "requested_loan_amount": 8000.0,
        "loan_purpose": "EMERGENCY_EXPENSE",
        "loan_term_months": 24,
        "interest_rate_pct": 18.5,
        "declared_existing_monthly_debt": 400.0,
        "declared_monthly_housing_expense": 650.0,
        "dependents_count": 0,
        "bankruptcies_count": 1,  # Recent bankruptcy knockout
        "tax_liens_count": 0,
        "persona_type": "GOLDEN_KNOCKOUT_FAIL",
        "expected_verdict": "DECLINE_RECOMMENDED",
        "notes": "Triple policy knockout: Credit score < 600, monthly income < $2,000, active recent bankruptcy, and DTI > 55%."
    }
]

# First and last names for generating remaining synthetic profiles
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker"
]

EMPLOYERS = [
    ("Global Tech Solutions", "Software Engineer", 95000, 140000),
    ("City General Hospital", "Registered Nurse", 68000, 92000),
    ("Pinnacle Financial Partners", "Account Executive", 60000, 88000),
    ("Alliance Logistics", "Fleet Dispatcher", 45000, 62000),
    ("Oakland School District", "Secondary Educator", 52000, 70000),
    ("Metro Retail Management", "Store Manager", 48000, 65000),
    ("Precision Engineering Co.", "Mechanical Technician", 58000, 80000),
    ("Beacon Media Group", "Content Strategist", 55000, 75000)
]

def generate_applicant_pool(total_count=50):
    """Generates the full list of applicants including golden personas and realistic synthetic records."""
    applicants = []
    
    # 1. Add Golden Personas
    for p in GOLDEN_PERSONAS:
        app = p.copy()
        pmt = calculate_monthly_payment(app["requested_loan_amount"], app["interest_rate_pct"], app["loan_term_months"])
        app["estimated_monthly_payment"] = pmt
        total_debt_service = app["declared_existing_monthly_debt"] + pmt
        app["calculated_dti_pct"] = round((total_debt_service / app["declared_monthly_net_income"]) * 100, 2)
        app["calculated_lti_ratio"] = round(app["requested_loan_amount"] / app["declared_annual_income"], 2)
        app["application_date"] = "2026-03-01"
        applicants.append(app)
        
    # 2. Add remaining realistic synthetic applicants
    for i in range(len(GOLDEN_PERSONAS) + 1, total_count + 1):
        cust_id = f"CUST-{1000 + i}"
        app_id = f"APP-2026-{i:03d}"
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        age = random.randint(23, 62)
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(10, 99)}@example.com"
        phone = f"+1-555-0{random.randint(100, 999)}"
        address = f"{random.randint(100, 999)} {random.choice(['Maple', 'Oak', 'Washington', 'Highland', 'Sunset'])} {random.choice(['St', 'Ave', 'Blvd', 'Rd'])}, Chicago, IL"
        housing = random.choices(["RENT", "MORTGAGE", "OWN"], weights=[0.45, 0.45, 0.10])[0]
        housing_cost = random.randint(900, 2400) if housing != "OWN" else random.randint(200, 450)
        
        emp_company, emp_role, min_sal, max_sal = random.choice(EMPLOYERS)
        annual_income = round(random.uniform(min_sal, max_sal), -2)
        monthly_net = round((annual_income * 0.72) / 12.0, 2)
        
        # Credit Score distribution: realistic mix
        score_choice = random.choices(
            ["PRIME", "NEAR_PRIME", "SUBPRIME", "HIGH_RISK"],
            weights=[0.45, 0.35, 0.15, 0.05]
        )[0]
        
        if score_choice == "PRIME":
            score = random.randint(720, 810)
            tier = "TIER_1_PRIME"
            rate = round(random.uniform(6.5, 8.5), 2)
            loan_amt = round(random.uniform(10000, 35000), -2)
        elif score_choice == "NEAR_PRIME":
            score = random.randint(660, 719)
            tier = "TIER_2_NEAR_PRIME"
            rate = round(random.uniform(8.9, 12.5), 2)
            loan_amt = round(random.uniform(8000, 25000), -2)
        elif score_choice == "SUBPRIME":
            score = random.randint(600, 659)
            tier = "TIER_3_SUBPRIME"
            rate = round(random.uniform(13.0, 17.5), 2)
            loan_amt = round(random.uniform(4000, 15000), -2)
        else:
            score = random.randint(520, 595)
            tier = "TIER_4_HIGH_RISK"
            rate = round(random.uniform(18.0, 24.0), 2)
            loan_amt = round(random.uniform(3000, 10000), -2)
            
        term = random.choice([24, 36, 48, 60])
        purpose = random.choice(["DEBT_CONSOLIDATION", "HOME_IMPROVEMENT", "MAJOR_PURCHASE", "MEDICAL_EXPENSES", "AUTO_REPAIR"])
        existing_debt = round(random.uniform(200, 800), 2)
        
        pmt = calculate_monthly_payment(loan_amt, rate, term)
        total_debt_service = existing_debt + pmt
        dti = round((total_debt_service / monthly_net) * 100, 2)
        lti = round(loan_amt / annual_income, 2)
        
        expected_verdict = "ELIGIBLE_FOR_APPROVAL" if (score >= 660 and dti <= 35.0) else (
            "FURTHER_REVIEW_REQUIRED" if (score >= 600 and dti <= 43.0) else "DECLINE_RECOMMENDED"
        )
        
        app = {
            "applicant_id": cust_id,
            "application_id": app_id,
            "full_name": full_name,
            "age": age,
            "email": email,
            "phone": phone,
            "address": address,
            "housing_status": housing,
            "employment_status": "EMPLOYED_FULL_TIME",
            "employer_name": emp_company,
            "job_title": emp_role,
            "employment_length_months": random.randint(8, 72),
            "declared_annual_income": annual_income,
            "declared_monthly_net_income": monthly_net,
            "actual_monthly_salary": monthly_net,
            "credit_score": score,
            "credit_score_tier": tier,
            "requested_loan_amount": loan_amt,
            "loan_purpose": purpose,
            "loan_term_months": term,
            "interest_rate_pct": rate,
            "estimated_monthly_payment": pmt,
            "declared_existing_monthly_debt": existing_debt,
            "declared_monthly_housing_expense": housing_cost,
            "dependents_count": random.choice([0, 1, 2]),
            "bankruptcies_count": 0,
            "tax_liens_count": 0,
            "calculated_dti_pct": dti,
            "calculated_lti_ratio": lti,
            "application_date": "2026-03-01",
            "persona_type": "STANDARD_SYNTHETIC",
            "expected_verdict": expected_verdict,
            "notes": "Standard generated applicant profile."
        }
        applicants.append(app)
        
    return applicants


def generate_transactions_for_applicant(applicant, start_date=date(2025, 12, 1), end_date=date(2026, 2, 28)):
    """Generates a realistic 90-day time series of bank transactions with running balances and targeted anomalies."""
    txns = []
    cust_id = applicant["applicant_id"]
    account_id = f"ACC-{cust_id.split('-')[-1]}"
    persona = applicant.get("persona_type", "STANDARD_SYNTHETIC")
    
    # Starting initial balance
    if persona == "GOLDEN_PRIME_APPROVAL":
        balance = 12500.00
    elif persona == "GOLDEN_GAMBLING_NSF":
        balance = 1450.00
    elif persona == "GOLDEN_KNOCKOUT_FAIL":
        balance = 320.00
    else:
        balance = round(random.uniform(2500, 6500), 2)
        
    current_date = start_date
    txn_counter = 1
    
    # Semi-monthly payroll dates: 1st and 15th
    actual_salary = applicant.get("actual_monthly_salary", applicant["declared_monthly_net_income"])
    payroll_installment = round(actual_salary / 2.0, 2)
    
    while current_date <= end_date:
        day = current_date.day
        
        # --- 1. PAYROLL INFLOWS (1st and 15th of each month) ---
        if day in [1, 15]:
            balance += payroll_installment
            txns.append({
                "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                "applicant_id": cust_id,
                "account_id": account_id,
                "date": current_date.isoformat(),
                "type": "CREDIT",
                "category": "PAYROLL",
                "amount": payroll_installment,
                "running_balance": round(balance, 2),
                "merchant_or_description": f"{applicant['employer_name']} - DIRECT DEP PAYROLL",
                "flagged_anomaly": False,
                "anomaly_reason": ""
            })
            txn_counter += 1
            
        # --- 2. RENT / MORTGAGE (1st of each month) ---
        if day == 1:
            rent_amt = applicant["declared_monthly_housing_expense"]
            balance -= rent_amt
            txns.append({
                "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                "applicant_id": cust_id,
                "account_id": account_id,
                "date": current_date.isoformat(),
                "type": "DEBIT",
                "category": "HOUSING_RENT" if applicant["housing_status"] == "RENT" else "MORTGAGE",
                "amount": rent_amt,
                "running_balance": round(balance, 2),
                "merchant_or_description": "ACH Housing Payment - Landlord / Mortgage Servicer",
                "flagged_anomaly": False,
                "anomaly_reason": ""
            })
            txn_counter += 1
            
        # --- 3. DECLARED DEBT PAYMENTS (5th of each month) ---
        if day == 5 and applicant["declared_existing_monthly_debt"] > 0:
            debt_amt = applicant["declared_existing_monthly_debt"]
            balance -= debt_amt
            txns.append({
                "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                "applicant_id": cust_id,
                "account_id": account_id,
                "date": current_date.isoformat(),
                "type": "DEBIT",
                "category": "DEBT_SERVICE_DECLARED",
                "amount": debt_amt,
                "running_balance": round(balance, 2),
                "merchant_or_description": "Auto Finance Corp - Monthly Loan Installment",
                "flagged_anomaly": False,
                "anomaly_reason": ""
            })
            txn_counter += 1

        # --- 4. TARGETED PERSONA ANOMALIES & BEHAVIORS ---
        
        # Golden Persona 2: Window Dressing Deposit on Feb 16th (12 days before application)
        if persona == "GOLDEN_INCOME_DISCREPANCY" and current_date == date(2026, 2, 16):
            window_dress_amt = 15000.00
            balance += window_dress_amt
            txns.append({
                "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                "applicant_id": cust_id,
                "account_id": account_id,
                "date": current_date.isoformat(),
                "type": "CREDIT",
                "category": "CASH_DEPOSIT_UNUSUAL",
                "amount": window_dress_amt,
                "running_balance": round(balance, 2),
                "merchant_or_description": "INCOMING WIRE TRANSFER - UNVERIFIED THIRD PARTY",
                "flagged_anomaly": True,
                "anomaly_reason": "WINDOW_DRESSING_DEPOSIT (Rule POL-TXN-004)"
            })
            txn_counter += 1

        # Golden Persona 3: Gambling Spree & NSF Fees
        if persona == "GOLDEN_GAMBLING_NSF":
            # Gambling debits multiple times a week
            if current_date.weekday() in [4, 5] and random.random() < 0.7:  # Fri/Sat
                gambling_amt = round(random.choice([150.0, 250.0, 380.0, 520.0]), 2)
                balance -= gambling_amt
                is_large = gambling_amt > 500.0
                txns.append({
                    "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                    "applicant_id": cust_id,
                    "account_id": account_id,
                    "date": current_date.isoformat(),
                    "type": "DEBIT",
                    "category": "GAMBLING",
                    "amount": gambling_amt,
                    "running_balance": round(balance, 2),
                    "merchant_or_description": random.choice(["DraftKings Interactive", "BetMGM Sportsbook", "Golden Nugget Online"]),
                    "flagged_anomaly": True,
                    "anomaly_reason": "GAMBLING_EXCESSIVE_TRANSACTION (Rule POL-TXN-001)"
                })
                txn_counter += 1

            # NSF fees on specific dates
            if current_date in [date(2026, 1, 14), date(2026, 1, 29), date(2026, 2, 13), date(2026, 2, 27)]:
                nsf_fee = 35.00
                balance -= nsf_fee
                txns.append({
                    "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                    "applicant_id": cust_id,
                    "account_id": account_id,
                    "date": current_date.isoformat(),
                    "type": "DEBIT",
                    "category": "BANK_FEE",
                    "amount": nsf_fee,
                    "running_balance": round(balance, 2),
                    "merchant_or_description": "OVERDRAFT / RETURNED ITEM NSF FEE",
                    "flagged_anomaly": True,
                    "anomaly_reason": "NSF_RETURNED_ITEM_FEE (Rule POL-TXN-002)"
                })
                txn_counter += 1

        # Golden Persona 4: Undisclosed Debts (Klarna, Affirm, Microloan)
        if persona == "GOLDEN_UNDISCLOSED_DEBT":
            if day == 8:
                balance -= 180.00
                txns.append({
                    "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                    "applicant_id": cust_id,
                    "account_id": account_id,
                    "date": current_date.isoformat(),
                    "type": "DEBIT",
                    "category": "DEBT_SERVICE_UNDISCLOSED",
                    "amount": 180.00,
                    "running_balance": round(balance, 2),
                    "merchant_or_description": "Klarna Installment Auto-Debit #2/4",
                    "flagged_anomaly": True,
                    "anomaly_reason": "UNDISCLOSED_DEBT_OBLIGATION (Rule POL-TXN-003)"
                })
                txn_counter += 1
            if day == 18:
                balance -= 140.00
                txns.append({
                    "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                    "applicant_id": cust_id,
                    "account_id": account_id,
                    "date": current_date.isoformat(),
                    "type": "DEBIT",
                    "category": "DEBT_SERVICE_UNDISCLOSED",
                    "amount": 140.00,
                    "running_balance": round(balance, 2),
                    "merchant_or_description": "Affirm Inc Recurring Loan Debit",
                    "flagged_anomaly": True,
                    "anomaly_reason": "UNDISCLOSED_DEBT_OBLIGATION (Rule POL-TXN-003)"
                })
                txn_counter += 1
            if day == 22:
                balance -= 420.00
                txns.append({
                    "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                    "applicant_id": cust_id,
                    "account_id": account_id,
                    "date": current_date.isoformat(),
                    "type": "DEBIT",
                    "category": "DEBT_SERVICE_UNDISCLOSED",
                    "amount": 420.00,
                    "running_balance": round(balance, 2),
                    "merchant_or_description": "Avant Online Personal Credit Repayment",
                    "flagged_anomaly": True,
                    "anomaly_reason": "UNDISCLOSED_DEBT_OBLIGATION (Rule POL-TXN-003)"
                })
                txn_counter += 1

        # --- 5. EVERYDAY LIVING EXPENSES (Groceries, Utilities, Dining, Gas) ---
        if random.random() < 0.65:
            expense_cat = random.choice(["GROCERIES", "FOOD_DINING", "TRANSPORTATION", "UTILITIES", "SHOPPING"])
            if expense_cat == "GROCERIES":
                amount = round(random.uniform(45.0, 160.0), 2)
                desc = random.choice(["Kroger Supermarket", "Trader Joe's", "Whole Foods Market", "Costco Wholesale"])
            elif expense_cat == "FOOD_DINING":
                amount = round(random.uniform(15.0, 75.0), 2)
                desc = random.choice(["Starbucks Coffee", "Chipotle Mexican Grill", "DoorDash Food Delivery", "Local Bistro & Grill"])
            elif expense_cat == "TRANSPORTATION":
                amount = round(random.uniform(35.0, 65.0), 2)
                desc = random.choice(["Shell Oil Gas Station", "BP Express Fuel", "Chevron Station", "Uber Technologies"])
            elif expense_cat == "UTILITIES":
                amount = round(random.uniform(60.0, 150.0), 2)
                desc = random.choice(["Consolidated Edison Power", "Comcast Xfinity Internet", "City Water & Sewer"])
            else:
                amount = round(random.uniform(20.0, 95.0), 2)
                desc = random.choice(["Amazon.com Marketplace", "Target Store #1120", "CVS Pharmacy", "Walgreens"])

            balance -= amount
            txns.append({
                "transaction_id": f"TXN-{cust_id}-{txn_counter:04d}",
                "applicant_id": cust_id,
                "account_id": account_id,
                "date": current_date.isoformat(),
                "type": "DEBIT",
                "category": expense_cat,
                "amount": amount,
                "running_balance": round(balance, 2),
                "merchant_or_description": desc,
                "flagged_anomaly": False,
                "anomaly_reason": ""
            })
            txn_counter += 1

        current_date += timedelta(days=1)
        
    return txns


def main():
    print("Generating Credit-Risk synthetic dataset...")
    applicants = generate_applicant_pool(total_count=50)
    
    # 1. Save applications.csv
    app_csv_path = os.path.join(PROCESSED_DIR, "applications.csv")
    fieldnames = list(applicants[0].keys())
    with open(app_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(applicants)
    print(f"Saved {len(applicants)} applicants to {app_csv_path}")

    # 2. Save applications.json
    app_json_path = os.path.join(PROCESSED_DIR, "applications.json")
    with open(app_json_path, mode="w", encoding="utf-8") as f:
        json.dump(applicants, f, indent=2)
    print(f"Saved applications JSON to {app_json_path}")

    # 3. Generate Transactions
    all_transactions = []
    for app in applicants:
        txns = generate_transactions_for_applicant(app)
        all_transactions.extend(txns)

    # 4. Save transactions.csv
    txn_csv_path = os.path.join(PROCESSED_DIR, "transactions.csv")
    txn_fieldnames = list(all_transactions[0].keys())
    with open(txn_csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=txn_fieldnames)
        writer.writeheader()
        writer.writerows(all_transactions)
    print(f"Saved {len(all_transactions)} transactions to {txn_csv_path}")

    # 5. Save transactions.json
    txn_json_path = os.path.join(PROCESSED_DIR, "transactions.json")
    with open(txn_json_path, mode="w", encoding="utf-8") as f:
        json.dump(all_transactions, f, indent=2)
    print(f"Saved transactions JSON to {txn_json_path}")

    # 6. Save Golden Demo Cases Guide
    golden_cases = [app for app in applicants if app.get("persona_type", "").startswith("GOLDEN_")]
    golden_path = os.path.join(TEST_CASES_DIR, "golden_demo_cases.json")
    with open(golden_path, mode="w", encoding="utf-8") as f:
        json.dump(golden_cases, f, indent=2)
    print(f"Saved {len(golden_cases)} golden test personas to {golden_path}")

    print("\nDataset generation successfully completed!")


if __name__ == "__main__":
    main()
