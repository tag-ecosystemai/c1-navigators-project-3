from ai_engineering.orchestrator.orchestrator import investigate

sample_input = {
    "application": {
        "income": 5000,
        "expenses": 2000,
        "loan_amount": 15000,
        "tenure_months": 24
    },
    "transactions": [],
    "policies": []
}

result = investigate(sample_input)
print(result)
