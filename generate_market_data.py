import json
import random

# Constants
sectors = ["Banking", "NBFC", "Technology", "Healthcare", "Energy", "FMCG", "Telecom", "Pharma"]
categories = ["Equity", "Debt", "Hybrid", "Index", "Thematic"]
banks = ["SafeBank", "TrustBank", "GrowBank", "NeoBank", "SecureBank"]

# Generate 25 mock stocks
stocks = [
    {
        "symbol": f"SYM{i:03}",
        "name": f"Company{i:03} Ltd",
        "sector": random.choice(sectors),
        "growth_pct_yoy": round(random.uniform(5.0, 25.0), 2)
    }
    for i in range(1, 11)
]

# Generate 25 mock mutual funds
mutual_funds = [
    {
        "code": f"MF_{cat[:2].upper()}_{i:03}",
        "name": f"{cat} Fund {i}",
        "category": cat,
        "return_pct_3y_cagr": round(random.uniform(6.0, 18.0), 2)
    }
    for i, cat in zip(range(1, 11), [random.choice(categories) for _ in range(11)])
]

# Generate 25 mock fixed deposit options
fixed_deposits = [
    {
        "bank": random.choice(banks),
        "tenure_months": random.choice([6, 12, 24, 36, 48, 60]),
        "rate_pct": round(random.uniform(5.0, 8.5), 2)
    }
    for _ in range(11)
]

# Construct final market data structure
market_data = {
    "as_of": "2025-06-30",
    "currency": "INR",
    "stocks": stocks,
    "mutual_funds": mutual_funds,
    "fixed_deposits": fixed_deposits
}

# Save to JSON
with open("market_data.json", "w") as f:
    json.dump(market_data, f, indent=2)

print("✅ market_data.json with 11 entries per category has been created.")
