from typing import Dict, Any, List, Optional, TypedDict

class GraphState(TypedDict):
    # User data
    user_id: int
    user_profile: Optional[Dict[str, Any]]
    
    # Market data
    market_data: Optional[Dict[str, Any]]
    processed_market_data: Optional[Dict[str, Any]]
    
    # Analysis results
    emergency_fund: Optional[float]
    risk_profile: Optional[str]
    time_horizon: Optional[int]
    
    # Allocation
    asset_allocation: Optional[Dict[str, float]]
    selected_stocks: Optional[List[Dict[str, Any]]]
    selected_mutual_funds: Optional[List[Dict[str, Any]]]
    selected_fds: Optional[List[Dict[str, Any]]]
    
    # Final output
    recommendation: Optional[Dict[str, Any]]
    
    # Status
    status: Optional[str]
    error: Optional[str]

# Default asset allocations for different risk profiles
DEFAULT_ALLOCATIONS = {
    "low": {
        "equity": 0.3,
        "fixed_income": 0.5,
        "cash": 0.2,
        "description": "Conservative portfolio with focus on capital preservation"
    },
    "medium": {
        "equity": 0.6,
        "fixed_income": 0.3,
        "cash": 0.1,
        "description": "Balanced portfolio with moderate growth potential"
    },
    "high": {
        "equity": 0.8,
        "fixed_income": 0.15,
        "cash": 0.05,
        "description": "Aggressive portfolio with high growth potential"
    }
}

# Risk profiles and their asset allocations
RISK_PROFILES = {
    "Low": {"equity": 0.4, "fixed_income": 0.4, "gold": 0.1, "cash": 0.1},
    "Medium": {"equity": 0.6, "fixed_income": 0.3, "gold": 0.1, "cash": 0.0},
    "High": {"equity": 0.8, "fixed_income": 0.15, "gold": 0.05, "cash": 0.0}
}

# Constants
ASSET_CLASSES = ["equity", "fixed_income", "gold", "cash"]
