from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import sqlite3
from tools import get_all_tools
from models import GraphState, DEFAULT_ALLOCATIONS, RISK_PROFILES

# Initialize tools
tools = get_all_tools()
user_profile_tool = tools[0]  # UserProfileTool
market_data_tool = tools[1]   # MarketDataTool
portfolio_tool = tools[2]     # PortfolioTool

def fetch_user_profile(state: GraphState) -> Dict[str, Any]:
    """Node to fetch user profile."""
    print("---NODE: Fetching User Profile---")
    try:
        # Ensure we have a valid state
        if not isinstance(state, dict):
            state = {}
            
        user_id = state.get("user_id")
        if not user_id:
            return {
                **state,
                "error": "No user_id provided in state",
                "status": "error"
            }
            
        print(f"🛠️ TOOL: Fetching profile for user_id: {user_id}")
        data = user_profile_tool._run(user_id)
        
        if "error" in data:
            error_msg = f"Failed to fetch user profile: {data['error']}"
            print(f"ERROR: {error_msg}")
            return {
                **state,
                "error": error_msg,
                "status": "error"
            }
        
        if not isinstance(data, dict):
            error_msg = "Invalid profile data format"
            print(f"ERROR: {error_msg}")
            return {
                **state,
                "error": error_msg,
                "status": "error"
            }
            
        # Ensure required fields are present
        required_fields = ['monthly_income', 'monthly_expenses', 'risk_appetite']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        
        if missing_fields:
            error_msg = f"Profile is missing required fields: {', '.join(missing_fields)}"
            print(f"ERROR: {error_msg}")
            return {
                **state,
                "error": error_msg,
                "status": "error"
            }
            
        # Return updated state with user profile
        new_state = {
            **state,
            "user_profile": data,
            "status": "success"  # Changed from 'profile_fetched' to 'success' for consistency
        }
        
        print(f"✅ Successfully fetched profile for user_id: {user_id}")
        return new_state
        
    except Exception as e:
        error_msg = f"Failed to fetch user profile: {str(e)}"
        print(f"ERROR in fetch_user_profile: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }

def calculate_savings(monthly_income: float, monthly_expenses: float) -> Dict[str, float]:
    """Calculate savings and investment amounts based on income and expenses."""
    if not all(isinstance(x, (int, float)) for x in [monthly_income, monthly_expenses]):
        return {}
        
    disposable_income = monthly_income - monthly_expenses
    emergency_fund = 0.05 * disposable_income  # 5% of disposable income
    monthly_investment = disposable_income - emergency_fund
    
    return {
        'emergency_fund': emergency_fund,
        'monthly_investment': monthly_investment,
        'disposable_income': disposable_income
    }

def check_profile_completeness(state: GraphState) -> Dict[str, Any]:
    """Check if user profile is complete and valid."""
    print("---NODE: Checking Profile Completeness---")
    
    # Ensure we have a valid state and profile
    if not isinstance(state, dict):
        state = {}
    
    profile = state.get("user_profile", {})
    if not isinstance(profile, dict):
        return {
            **state,
            "error": "Invalid profile data format",
            "status": "error"
        }
    
    # Required base fields (excluding derived fields)
    required_fields = [
        'monthly_income', 'monthly_expenses',
        'risk_appetite', 'investment_horizon_years'
    ]
    
    # Check for missing base fields
    missing = [field for field in required_fields 
              if field not in profile or profile[field] is None]
    
    if missing:
        print(f"Profile incomplete. Missing fields: {', '.join(missing)}")
        return {
            **state,
            "status": "profile_incomplete",
            "missing_fields": missing,
            "error": f"Missing required fields: {', '.join(missing)}"
        }
    
    try:
        # Convert numeric fields to float
        monthly_income = float(profile['monthly_income'])
        monthly_expenses = float(profile['monthly_expenses'])
        
        # Calculate derived fields
        savings_info = calculate_savings(monthly_income, monthly_expenses)
        if savings_info:
            profile.update(savings_info)
        
        # Set default investment goals if not provided
        if 'investment_goals' not in profile or not profile['investment_goals']:
            profile['investment_goals'] = ["Wealth accumulation", "Retirement planning"]
        
        # Normalize risk profile
        risk_appetite = str(profile.get('risk_appetite', '')).strip()
        risk_mapping = {
            'low': 'Low',
            'medium': 'Medium',
            'high': 'High'
        }
        
        risk_appetite_lower = risk_appetite.lower()
        if risk_appetite_lower not in risk_mapping:
            raise ValueError(f"Invalid risk profile: {risk_appetite}")
        
        normalized_risk = risk_mapping[risk_appetite_lower]
        profile['risk_appetite'] = normalized_risk
        
        # Update the state with processed profile
        state["user_profile"] = profile
        
        return {
            **state,
            "status": "profile_valid"
        }
        
    except ValueError as ve:
        error_msg = f"Invalid profile data: {str(ve)}"
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "status": "profile_invalid",
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error processing profile: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "status": "error",
            "error": error_msg
        }

def generate_fallback_recommendation(state: GraphState) -> Dict[str, Any]:
    """Generate a basic recommendation when profile is incomplete."""
    print("---NODE: Generating Fallback Recommendation---")
    
    # Get the reason for the fallback
    status = state.get("status", "profile_incomplete")
    message = "Please complete your profile to get personalized recommendations."
    
    if status == "profile_incomplete":
        missing = state.get("missing_fields", [])
        if missing:
            message = f"Please provide the following information: {', '.join(missing)}."
    elif status == "profile_invalid":
        message = state.get("error", "Invalid profile information provided.")
    
    return {
        **state,
        "recommendation": {
            "status": "fallback",
            "message": message,
            "suggested_actions": [
                "Update your financial information",
                "Set clear investment goals",
                "Complete your risk assessment"
            ],
            "generated_at": datetime.now().isoformat(),
            "user_id": state.get("user_id")
        },
        "status": "completed_with_fallback"
    }

def fetch_market_data(state: GraphState) -> Dict[str, Any]:
    """Node to fetch market data."""
    print("---NODE: Fetching Market Data---")
    try:
        # Ensure we have a valid state
        if not isinstance(state, dict):
            state = {}
            
        print("🛠️ TOOL: Fetching market data...")
        data = market_data_tool._run()
        
        if not isinstance(data, dict):
            raise ValueError("Invalid market data format")
            
        if "error" in data:
            error_msg = f"Market data error: {data['error']}"
            print(f"ERROR: {error_msg}")
            return {
                **state,
                "error": error_msg,
                "status": "error"
            }
            
        print("✅ TOOL: Successfully fetched market data.")
        return {
            **state,
            "market_data": data, 
            "status": "market_data_fetched"
        }
        
    except Exception as e:
        error_msg = f"Failed to fetch market data: {str(e)}"
        print(f"ERROR in fetch_market_data: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }

def preprocess_market_data(state: GraphState) -> Dict[str, Any]:
    """Preprocess and filter market data based on user profile."""
    print("---NODE: Preprocessing Market Data---")
    try:
        # Ensure we have a valid state
        if not isinstance(state, dict):
            state = {}
            
        market_data = state.get("market_data", {})
        user_profile = state.get("user_profile", {})
        
        if not market_data:
            raise ValueError("No market data available for processing")
        
        # Add any preprocessing logic here (filtering, sorting, etc.)
        processed_data = {
            "stocks": market_data.get("stocks", []),
            "mutual_funds": market_data.get("mutual_funds", []),
            "fixed_deposits": market_data.get("fixed_deposits", [])
        }
        
        # Add any additional processing based on user profile
        risk_profile = user_profile.get("risk_appetite", "Medium").lower()
        
        # Filter products based on risk profile if needed
        if risk_profile == "low":
            processed_data["stocks"] = [s for s in processed_data.get("stocks", []) if s.get("risk_level", "").lower() == "low"]
        elif risk_profile == "high":
            # Include all stocks for high-risk profiles
            pass
        
        return {
            **state,
            "processed_market_data": processed_data, 
            "status": "market_data_processed"
        }
        
    except Exception as e:
        error_msg = f"Error processing market data: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }

def calculate_emergency_fund(state: GraphState) -> Dict[str, Any]:
    """
    Calculate emergency fund and monthly investment amount.
    
    Emergency fund = 5% of (monthly_income - monthly_expenses)
    Monthly investment = 95% of (monthly_income - monthly_expenses)
    """
    print("---NODE: Calculating Emergency Fund and Monthly Investment---")
    
    try:
        # Ensure we have a valid state
        if not isinstance(state, dict):
            state = {}
            
        profile = state.get("user_profile", {})
        
        # Get monthly income and expenses, default to 0 if not provided
        monthly_income = float(profile.get("monthly_income", 0))
        monthly_expenses = float(profile.get("monthly_expenses", 0))
        
        # Calculate disposable income
        disposable_income = monthly_income - monthly_expenses
        
        if disposable_income <= 0:
            raise ValueError("Monthly expenses exceed or equal monthly income")
            
        # Calculate emergency fund (5% of disposable income)
        emergency_fund = round(disposable_income * 0.05, 2)
        
        # Calculate monthly investment (95% of disposable income)
        monthly_investment = round(disposable_income * 0.95, 2)
        
        print(f"💰 Emergency Fund: ₹{emergency_fund:,.2f}")
        print(f"💵 Monthly Investment: ₹{monthly_investment:,.2f}")
        
        # Update the profile with the calculated values
        updated_profile = {
            **profile,
            "emergency_fund": emergency_fund,
            "monthly_investment": monthly_investment
        }
        
        return {
            **state,
            "user_profile": updated_profile,
            "emergency_fund": emergency_fund,
            "monthly_investment": monthly_investment,
            "status": "emergency_fund_calculated"
        }
        
    except ValueError as ve:
        error_msg = str(ve)
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }
    except Exception as e:
        error_msg = f"Error calculating emergency fund: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }

def analyze_goals_and_risk(state: GraphState) -> GraphState:
    """Analyze user's financial goals and determine risk profile."""
    print("---NODE: Analyzing Goals and Risk---")
    profile = state.get("user_profile", {})
    
    # Get risk profile from user profile, default to 'moderate'
    risk_profile = profile.get("risk_appetite", "moderate").lower()
    if risk_profile not in RISK_PROFILES:
        risk_profile = "moderate"
    
    # Get time horizon in years, default to 5 years
    time_horizon = int(profile.get("investment_horizon_years", 5))
    
    return {
        "risk_profile": risk_profile,
        "time_horizon": time_horizon,
        "status": "risk_analyzed"
    }

def define_risk_based_allocation(state: GraphState) -> Dict[str, Any]:
    """Define asset allocation based on risk profile."""
    print("---NODE: Defining Risk-Based Allocation---")
    
    try:
        # Ensure we have a valid state
        if not isinstance(state, dict):
            state = {}
            
        # Get risk profile from state, default to 'medium' if not found
        risk_profile = state.get("risk_profile", "medium").lower()
        
        # Validate risk profile
        if risk_profile not in DEFAULT_ALLOCATIONS:
            print(f"Warning: Invalid risk profile '{risk_profile}'. Using 'medium' as default.")
            risk_profile = "medium"
        
        # Get the allocation for the risk profile
        allocation = DEFAULT_ALLOCATIONS[risk_profile].copy()
        
        # Add metadata
        allocation["risk_profile"] = risk_profile
        allocation["last_updated"] = datetime.now().isoformat()
        
        print(f"✅ Defined allocation for risk profile: {risk_profile}")
        return {
            **state,
            "asset_allocation": allocation,
            "status": "allocation_defined"
        }
        
    except Exception as e:
        error_msg = f"Error defining risk-based allocation: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }

def select_investment_products(state: GraphState) -> Dict[str, Any]:
    """
    Select specific investment products based on allocation and monthly investment amount.
    
    Args:
        state: Current state containing asset allocation, market data, and monthly investment
        
    Returns:
        Updated state with selected investment products and allocations
    """
    print("---NODE: Selecting Investment Products---")
    
    # Debug: Print current state keys and user profile keys
    print(f"Current state keys: {list(state.keys())}")
    user_profile = state.get("user_profile", {})
    print(f"User profile keys: {list(user_profile.keys())}")
    
    try:
        # Get the monthly investment amount from the state or user profile
        monthly_investment = state.get("monthly_investment")
        if monthly_investment is None:
            monthly_investment = user_profile.get("monthly_investment")
            if monthly_investment is None:
                # Calculate monthly investment if not set
                monthly_income = float(user_profile.get("monthly_income", 0))
                monthly_expenses = float(user_profile.get("monthly_expenses", 0))
                monthly_investment = (monthly_income - monthly_expenses) * 0.95  # 95% of disposable income
        
        monthly_investment = float(monthly_investment)
        print(f"Monthly investment from state: {monthly_investment}")
        
        if monthly_investment <= 0:
            raise ValueError("No monthly investment amount available")
            
        # Get the allocation from the state with defaults
        allocation = state.get("asset_allocation", {
            "equity": 0.6,
            "fixed_income": 0.3,
            "cash": 0.1
        })
        
        equity_ratio = allocation.get("equity", 0.6)
        fixed_income_ratio = allocation.get("fixed_income", 0.3)
        cash_ratio = allocation.get("cash", 0.1)
        
        # Ensure ratios sum to 1
        total_ratio = equity_ratio + fixed_income_ratio + cash_ratio
        if total_ratio > 0:
            equity_ratio /= total_ratio
            fixed_income_ratio /= total_ratio
            cash_ratio /= total_ratio
        
        # Calculate amounts for each asset class
        equity_amount = monthly_investment * equity_ratio
        fixed_income_amount = monthly_investment * fixed_income_ratio
        cash_amount = monthly_investment * cash_ratio
        
        print(f"📊 Allocation: Equity: ₹{equity_amount:,.2f}, "
              f"Fixed Income: ₹{fixed_income_amount:,.2f}, "
              f"Cash: ₹{cash_amount:,.2f}")
        
        # Get market data
        market_data = state.get("market_data", {})
        
        # Initialize selected products with empty lists
        selected_products = {
            "stocks": [],
            "mutual_funds": [],
            "fixed_deposits": [],
            "total_allocated": 0
        }
        
        # Select stocks for equity allocation
        if equity_amount > 0:
            stocks = sorted(
                market_data.get("stocks", []),
                key=lambda x: x.get("market_cap", 0),
                reverse=True
            )
            
            # Distribute equity amount among top 5 stocks
            num_stocks = min(5, len(stocks))
            if num_stocks > 0:
                per_stock = round(equity_amount / num_stocks, 2)
                selected_products["stocks"] = [
                    {**stock, "allocation_amount": per_stock}
                    for stock in stocks[:num_stocks]
                ]
        
        # Select mutual funds for fixed income allocation
        if fixed_income_amount > 0:
            mfs = sorted(
                [mf for mf in market_data.get("mutual_funds", []) 
                 if mf.get("category") == "debt"],
                key=lambda x: x.get("returns_5y", 0),
                reverse=True
            )
            
            # Distribute fixed income amount among top 3 funds
            num_mfs = min(3, len(mfs))
            if num_mfs > 0:
                per_mf = round(fixed_income_amount / num_mfs, 2)
                selected_products["mutual_funds"] = [
                    {**mf, "allocation_amount": per_mf}
                    for mf in mfs[:num_mfs]
                ]
        
        # Select fixed deposits for cash allocation
        if cash_amount > 0:
            fds = sorted(
                market_data.get("fixed_deposits", []),
                key=lambda x: float(x.get("interest_rate", 0)),
                reverse=True
            )
            
            # Distribute cash amount among top 3 FDs
            num_fds = min(3, len(fds))
            if num_fds > 0:
                per_fd = round(cash_amount / num_fds, 2)
                selected_products["fixed_deposits"] = [
                    {**fd, "allocation_amount": per_fd}
                    for fd in fds[:num_fds]
                ]
        
        # Ensure we have some default selections if no products were found
        if not selected_products["stocks"] and equity_amount > 0:
            selected_products["stocks"] = [
                {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Conglomerate", "allocation_amount": equity_amount}
            ]
            
        if not selected_products["mutual_funds"] and fixed_income_amount > 0:
            selected_products["mutual_funds"] = [
                {"scheme_name": "HDFC Top 100 Fund", "category": "Equity", "allocation_amount": fixed_income_amount}
            ]
            
        if not selected_products["fixed_deposits"] and cash_amount > 0:
            selected_products["fixed_deposits"] = [
                {"bank": "SBI", "tenure": "1 year", "interest_rate": 6.5, "allocation_amount": cash_amount}
            ]
        
        # Calculate total allocated amount
        total_allocated = sum(
            product["allocation_amount"]
            for product_type in ["stocks", "mutual_funds", "fixed_deposits"]
            for product in selected_products[product_type]
        )
        
        selected_products["total_allocated"] = round(total_allocated, 2)
        
        print(f"✅ Selected {len(selected_products['stocks'])} stocks, "
              f"{len(selected_products['mutual_funds'])} mutual funds, "
              f"and {len(selected_products['fixed_deposits'])} fixed deposits")
        print(f"💰 Total allocated: ₹{total_allocated:,.2f}")
        
        # Prepare suggested_instruments structure for the final recommendation
        suggested_instruments = {
            "stocks": [
                {
                    "name": stock.get("name", stock.get("symbol", "Unknown")),
                    "allocation_percentage": (stock["allocation_amount"] / monthly_investment * 100) if monthly_investment > 0 else 0,
                    "reason": f"Selected based on market cap in {stock.get('sector', 'various')} sector"
                }
                for stock in selected_products["stocks"]
            ],
            "mutual_funds": [
                {
                    "name": mf.get("scheme_name", "Unknown Fund"),
                    "allocation_percentage": (mf["allocation_amount"] / monthly_investment * 100) if monthly_investment > 0 else 0,
                    "reason": f"Selected based on historical returns in {mf.get('category', 'various')} category"
                }
                for mf in selected_products["mutual_funds"]
            ],
            "fixed_deposits": [
                {
                    "bank": fd.get("bank", "Unknown Bank"),
                    "tenure_months": int(fd.get("tenure", "12").split()[0]) * 12 if "year" in fd.get("tenure", "") else int(fd.get("tenure", "12").split()[0]),
                    "rate_pct": float(fd.get("interest_rate", 0)),
                    "allocation_percentage": (fd["allocation_amount"] / monthly_investment * 100) if monthly_investment > 0 else 0,
                    "reason": f"Selected based on interest rate of {fd.get('interest_rate', 0)}%"
                }
                for fd in selected_products["fixed_deposits"]
            ]
        }

        # Update the state with all calculated values
        new_state = {
            **state,
            "selected_products": selected_products,
            "suggested_instruments": {"suggested_instruments": suggested_instruments},
            "monthly_investment": monthly_investment,  # Ensure this is set in state
            "status": "products_selected"
        }
        
        # Debug: Print the keys we're returning
        print(f"Returning state with keys: {list(new_state.keys())}")
        
        return new_state
        
    except ValueError as ve:
        error_msg = str(ve)
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }
    except Exception as e:
        error_msg = f"Error selecting investment products: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }

def calculate_returns(state: GraphState) -> Dict[str, Any]:
    """
    Calculate projected returns for selected investments.
    
    Uses the monthly investment amount that already accounts for the emergency fund.
    """
    print("---NODE: Calculating Projected Returns---")
    
    try:
        # Get the monthly investment amount that already accounts for emergency fund
        monthly_investment = state.get("monthly_investment")
        if monthly_investment is None:
            # Fallback to user profile if not in state
            monthly_investment = state.get("user_profile", {}).get("monthly_investment", 0)
        
        monthly_investment = float(monthly_investment)
        
        if monthly_investment <= 0:
            raise ValueError("No monthly investment amount available for return calculation")
        
        print(f"📊 Using monthly investment for returns calculation: ₹{monthly_investment:,.2f}")
        
        # Apply allocation to monthly investment amount
        allocation = state.get("asset_allocation", {})
        equity_amount = monthly_investment * allocation.get("equity", 0)
        fixed_income_amount = monthly_investment * allocation.get("fixed_income", 0)
        gold_amount = monthly_investment * allocation.get("gold", 0)
        cash_amount = monthly_investment * allocation.get("cash", 0)
    
        # Calculate projected returns (simplified)
        # In a real app, you'd use historical data and more sophisticated models
        equity_return = equity_amount * 0.10  # 10% expected return for stocks
        fixed_income_return = fixed_income_amount * 0.06  # 6% for fixed income
        gold_return = gold_amount * 0.04  # 4% for gold
        cash_return = cash_amount * 0.03  # 3% for cash
        total_return = equity_return + fixed_income_return + gold_return + cash_return
        
        # Calculate ROI percentage based on total monthly investment
        roi_percentage = (total_return / monthly_investment) * 100 if monthly_investment > 0 else 0
        
        print(f"📈 Projected Returns (Annual):")
        print(f"  - Equity (10%): ₹{equity_return:,.2f}")
        print(f"  - Fixed Income (6%): ₹{fixed_income_return:,.2f}")
        print(f"  - Gold (4%): ₹{gold_return:,.2f}")
        print(f"  - Cash (3%): ₹{cash_return:,.2f}")
        print(f"  - Total: ₹{total_return:,.2f}")
        print(f"  - ROI: {roi_percentage:.2f}%")
        
        return {
            **state,
            "projected_returns": {
                "equity": equity_return,
                "fixed_income": fixed_income_return,
                "gold": gold_return,
                "cash": cash_return,
                "total": total_return,
                "roi_percentage": roi_percentage
            },
            "status": "returns_calculated"
        }
        
    except Exception as e:
        error_msg = f"Error calculating returns: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }

def generate_final_recommendation(state: GraphState) -> Dict[str, Any]:
    """
    Generate the final investment recommendation with all calculated values.
    
    Args:
        state: Current state containing all calculated values
        
    Returns:
        Dictionary containing the recommendation and status
    """
    print("---NODE: Generating Final Recommendation---")
    print(f"Current state keys: {list(state.keys())}")
    
    try:
        # Get all necessary values from state with debug logging
        user_profile = state.get("user_profile", {})
        print(f"User profile keys: {list(user_profile.keys())}")
        
        # Get values with fallbacks
        emergency_fund = float(state.get("emergency_fund", 0))
        monthly_investment = float(user_profile.get("monthly_investment", 0))
        if monthly_investment <= 0:  # Fallback to calculation if not set
            monthly_income = float(user_profile.get("monthly_income", 0))
            monthly_expenses = float(user_profile.get("monthly_expenses", 0))
            monthly_investment = (monthly_income - monthly_expenses) * 0.95  # 95% of disposable income
        
        # Get asset allocation with defaults
        asset_allocation = state.get("asset_allocation", {
            "equity": 0.6, 
            "fixed_income": 0.3, 
            "cash": 0.1
        })
        
        # Debug: Print all state keys for troubleshooting
        print(f"Debug - All state keys: {list(state.keys())}")
        
        # Get selected products from state or initialize empty
        selected_products = state.get("selected_products", {
            "stocks": [],
            "mutual_funds": [],
            "fixed_deposits": [],
            "total_allocated": 0
        })
        
        # Get suggested_instruments from state with better error handling
        suggested_instruments = {}
        
        # First, try to get from state directly
        if "suggested_instruments" in state:
            suggested_instruments = state["suggested_instruments"]
            print("Debug - Found suggested_instruments in state")
        # Then try to get from selected_products if it has the structure
        elif "selected_products" in state and any(
            key in state["selected_products"] 
            for key in ["stocks", "mutual_funds", "fixed_deposits"]
        ):
            print("Debug - Using selected_products as suggested_instruments")
            suggested_instruments = {
                "stocks": state["selected_products"].get("stocks", []),
                "mutual_funds": state["selected_products"].get("mutual_funds", []),
                "fixed_deposits": state["selected_products"].get("fixed_deposits", [])
            }
        
        # Ensure we have a proper structure with all required keys
        if not isinstance(suggested_instruments, dict):
            print("Warning: suggested_instruments is not a dictionary, initializing empty structure")
            suggested_instruments = {
                "stocks": [],
                "mutual_funds": [],
                "fixed_deposits": []
            }
        
        # Ensure all required keys exist
        for inst_type in ["stocks", "mutual_funds", "fixed_deposits"]:
            if inst_type not in suggested_instruments or not isinstance(suggested_instruments[inst_type], list):
                print(f"Warning: '{inst_type}' not in suggested_instruments or not a list, adding empty list")
                suggested_instruments[inst_type] = []
        
        print(f"Debug - Processed suggested_instruments: {json.dumps(suggested_instruments, indent=2)}")
        
        print(f"Debug - Processed suggested_instruments: {json.dumps(suggested_instruments, indent=2)}")
        
        # If we have suggested_instruments, use them to populate selected_products
        if any(suggested_instruments.values()):
            print("Using suggested_instruments for selected_products")
            print(f"Debug - suggested_instruments: {json.dumps(suggested_instruments, indent=2)}")
            
            # Process stocks from suggested_instruments
            stocks = []
            for stock in suggested_instruments.get("stocks", []):
                try:
                    alloc_pct = float(stock.get("allocation_percentage", 0))
                    alloc_amount = (monthly_investment * (alloc_pct / 100)) if monthly_investment > 0 else 0
                    stocks.append({
                        "name": stock.get("name", "Unknown"),
                        "symbol": stock.get("symbol", ""),
                        "sector": stock.get("sector", ""),
                        "allocation_percentage": alloc_pct,
                        "allocation_amount": alloc_amount,
                        "reason": stock.get("reason", "Recommended based on market analysis")
                    })
                except Exception as e:
                    print(f"Error processing stock: {e}")
            
            # Process mutual funds from suggested_instruments
            mutual_funds = []
            for mf in suggested_instruments.get("mutual_funds", []):
                try:
                    alloc_pct = float(mf.get("allocation_percentage", 0))
                    alloc_amount = (monthly_investment * (alloc_pct / 100)) if monthly_investment > 0 else 0
                    mutual_funds.append({
                        "name": mf.get("name", mf.get("scheme_name", "Unknown Fund")),
                        "category": mf.get("category", ""),
                        "fund_house": mf.get("fund_house", ""),
                        "allocation_percentage": alloc_pct,
                        "allocation_amount": alloc_amount,
                        "reason": mf.get("reason", "Diversified investment option")
                    })
                except Exception as e:
                    print(f"Error processing mutual fund: {e}")
            
            # Process fixed deposits from suggested_instruments
            fixed_deposits = []
            for fd in suggested_instruments.get("fixed_deposits", []):
                try:
                    alloc_pct = float(fd.get("allocation_percentage", 0))
                    alloc_amount = (monthly_investment * (alloc_pct / 100)) if monthly_investment > 0 else 0
                    fixed_deposits.append({
                        "bank": fd.get("bank", "Bank"),
                        "tenure_months": int(fd.get("tenure_months", 12)),
                        "interest_rate": float(fd.get("interest_rate", fd.get("rate_pct", 0))),
                        "allocation_percentage": alloc_pct,
                        "allocation_amount": alloc_amount,
                        "reason": fd.get("reason", "Low-risk fixed return investment")
                    })
                except Exception as e:
                    print(f"Error processing fixed deposit: {e}")
            
            # Calculate total allocation
            total_allocated = sum(
                item["allocation_amount"] 
                for category in [stocks, mutual_funds, fixed_deposits] 
                for item in category
            )
            
            # Update selected_products with processed instruments
            selected_products = {
                "stocks": stocks,
                "mutual_funds": mutual_funds,
                "fixed_deposits": fixed_deposits,
                "total_allocated": total_allocated
            }
            
            print(f"Processed {len(stocks)} stocks, {len(mutual_funds)} mutual funds, "
                  f"{len(fixed_deposits)} fixed deposits with total allocation: {total_allocated:,.2f}")
        else:
            print("No suggested_instruments found, using empty selected_products")
            
            print(f"Processed {len(stocks)} stocks, {len(mutual_funds)} mutual funds, "
                  f"{len(fixed_deposits)} fixed deposits with total allocation: "
                  f"{selected_products['total_allocated']:,.2f}")
            
            # Initialize totals
            total_stocks = 0
            total_mutual_funds = 0
            total_fixed_deposits = 0
            
            # Process stocks
            processed_stocks = []
            for item in stocks:
                try:
                    alloc_pct = float(item.get('allocation_percentage', 0))
                    alloc_amount = (monthly_investment * (alloc_pct / 100)) if monthly_investment > 0 else 0
                    processed_item = {
                        'name': item.get('name', 'Unknown'),
                        'allocation_percentage': alloc_pct,
                        'allocation_amount': alloc_amount,
                        'reason': item.get('reason', 'No reason provided')
                    }
                    processed_stocks.append(processed_item)
                    total_stocks += alloc_amount
                except Exception as e:
                    print(f"Error processing stock item {item}: {str(e)}")
            
            # Process mutual funds
            processed_mfs = []
            for item in mutual_funds:
                try:
                    alloc_pct = float(item.get('allocation_percentage', 0))
                    alloc_amount = (monthly_investment * (alloc_pct / 100)) if monthly_investment > 0 else 0
                    processed_item = {
                        'name': item.get('name', 'Unknown'),
                        'allocation_percentage': alloc_pct,
                        'allocation_amount': alloc_amount,
                        'reason': item.get('reason', 'No reason provided')
                    }
                    processed_mfs.append(processed_item)
                    total_mutual_funds += alloc_amount
                except Exception as e:
                    print(f"Error processing mutual fund item {item}: {str(e)}")
            
            # Process fixed deposits
            processed_fds = []
            for item in fixed_deposits:
                try:
                    alloc_pct = float(item.get('allocation_percentage', 0))
                    alloc_amount = (monthly_investment * (alloc_pct / 100)) if monthly_investment > 0 else 0
                    processed_item = {
                        'bank': item.get('bank', 'Unknown Bank'),
                        'tenure_months': item.get('tenure_months', 12),
                        'rate_pct': item.get('rate_pct', 0),
                        'allocation_percentage': alloc_pct,
                        'allocation_amount': alloc_amount,
                        'reason': item.get('reason', 'No reason provided')
                    }
                    processed_fds.append(processed_item)
                    total_fixed_deposits += alloc_amount
                except Exception as e:
                    print(f"Error processing fixed deposit item {item}: {str(e)}")
            
            # Calculate total allocated amount
            total_allocated = total_stocks + total_mutual_funds + total_fixed_deposits
            print(f"Total allocated: {total_allocated} (Stocks: {total_stocks}, MFs: {total_mutual_funds}, FDs: {total_fixed_deposits})")
            
            selected_products = {
                "stocks": processed_stocks,
                "mutual_funds": processed_mfs,
                "fixed_deposits": processed_fds,
                "total_allocated": total_allocated
            }
            print(f"Calculated total_allocated: ₹{total_allocated:,.2f}")
        
        # Get projected returns with defaults
        projected_returns = state.get("projected_returns", {
            "equity": monthly_investment * asset_allocation.get("equity", 0) * 0.10,  # 10% return
            "fixed_income": monthly_investment * asset_allocation.get("fixed_income", 0) * 0.06,  # 6% return
            "gold": 0,  # No gold allocation by default
            "cash": monthly_investment * asset_allocation.get("cash", 0) * 0.03,  # 3% return
            "total": 0,
            "roi_percentage": 0
        })
        
        # Ensure we have the suggested_instruments in the final output with proper structure
        final_suggested_instruments = {
            "stocks": [
                {
                    "name": s.get("name", stock.get("symbol", "Stock")),
                    "allocation_percentage": float(s.get("allocation_percentage", 0)),
                    "reason": s.get("reason", "Recommended based on market analysis")
                }
                for s in suggested_instruments.get("stocks", [])
            ],
            "mutual_funds": [
                {
                    "name": mf.get("name", mf.get("scheme_name", "Mutual Fund")),
                    "allocation_percentage": float(mf.get("allocation_percentage", 0)),
                    "reason": mf.get("reason", "Diversified investment option")
                }
                for mf in suggested_instruments.get("mutual_funds", [])
            ],
            "fixed_deposits": [
                {
                    "bank": fd.get("bank", "Bank"),
                    "tenure_months": int(fd.get("tenure_months", 12)),
                    "rate_pct": float(fd.get("interest_rate", fd.get("rate_pct", 0))),
                    "allocation_percentage": float(fd.get("allocation_percentage", 0)),
                    "reason": fd.get("reason", "Low-risk fixed return investment")
                }
                for fd in suggested_instruments.get("fixed_deposits", [])
            ]
        }      
        
        # Calculate total projected returns if not set
        if projected_returns.get("total", 0) == 0:
            projected_returns["total"] = sum([
                projected_returns.get("equity", 0),
                projected_returns.get("fixed_income", 0),
                projected_returns.get("gold", 0),
                projected_returns.get("cash", 0)
            ])
            
        # Calculate ROI percentage if not set
        if projected_returns.get("roi_percentage", 0) == 0 and monthly_investment > 0:
            projected_returns["roi_percentage"] = (projected_returns["total"] / monthly_investment) * 100
        
        # Format currency values with ₹ symbol
        def format_currency(amount):
            return f"₹{float(amount):,.2f}" if amount else "₹0.00"
        
        # Prepare the recommendation
        recommendation = {
            "user_id": state.get("user_id"),
            "generated_at": datetime.now().isoformat(),
            "personal_info": {
                "name": user_profile.get("name"),
                "email": user_profile.get("email"),
                "monthly_income": format_currency(user_profile.get("monthly_income")),
                "monthly_expenses": format_currency(user_profile.get("monthly_expenses")),
                "disposable_income": format_currency(user_profile.get("disposable_income"))
            },
            "investment_summary": {
                "emergency_fund": format_currency(emergency_fund),
                "monthly_investment": format_currency(monthly_investment),
                "risk_profile": state.get("risk_profile", "medium"),
                "time_horizon_years": state.get("time_horizon", 5)
            },
            "asset_allocation": {
                "equity": f"{asset_allocation.get('equity', 0) * 100:.1f}%",
                "fixed_income": f"{asset_allocation.get('fixed_income', 0) * 100:.1f}%",
                "cash": f"{asset_allocation.get('cash', 0) * 100:.1f}%"
            },
            "selected_investments": {
                "stocks": [
                    {
                        "name": stock.get("name", stock.get("symbol", "Unknown")),
                        "allocation_percentage": (stock.get("allocation_amount", 0) / monthly_investment * 100) if monthly_investment > 0 else 0,
                        "allocation_amount": format_currency(stock.get("allocation_amount", 0)),
                        "reason": stock.get("reason", "Selected based on market analysis")
                    }
                    for stock in selected_products.get("stocks", [])
                ],
                "mutual_funds": [
                    {
                        "name": mf.get("scheme_name", mf.get("name", "Unknown Fund")),
                        "allocation_percentage": (mf.get("allocation_amount", 0) / monthly_investment * 100) if monthly_investment > 0 else 0,
                        "allocation_amount": format_currency(mf.get("allocation_amount", 0)),
                        "reason": mf.get("reason", f"Selected from {mf.get('category', 'various')} category")
                    }
                    for mf in selected_products.get("mutual_funds", [])
                ],
                "fixed_deposits": [
                    {
                        "bank": fd.get("bank", "Unknown Bank"),
                        "tenure_months": fd.get("tenure_months", 12),
                        "interest_rate": fd.get("interest_rate", 0),
                        "allocation_percentage": (fd.get("allocation_amount", 0) / monthly_investment * 100) if monthly_investment > 0 else 0,
                        "allocation_amount": format_currency(fd.get("allocation_amount", 0)),
                        "reason": fd.get("reason", f"Selected with interest rate of {fd.get('interest_rate', 0)}%")
                    }
                    for fd in selected_products.get("fixed_deposits", [])
                ],
                "total_allocated": format_currency(selected_products.get("total_allocated", 0))
            },
            "suggested_instruments": final_suggested_instruments,  # Include the processed suggested instruments
            "projected_returns": {
                "equity": format_currency(projected_returns.get("equity", 0)),
                "fixed_income": format_currency(projected_returns.get("fixed_income", 0)),
                "gold": format_currency(projected_returns.get("gold", 0)),
                "cash": format_currency(projected_returns.get("cash", 0)),
                "total": format_currency(projected_returns.get("total", 0)),
                "roi_percentage": f"{float(projected_returns.get('roi_percentage', 0)):.2f}%"
            },
            "status": "success",
            "message": "Investment recommendation generated successfully"
        }
        
        print("✅ Final recommendation generated successfully")
        return {
            **state,
            "recommendation": recommendation,
            "status": "recommendation_generated"
        }
        
    except Exception as e:
        error_msg = f"Error generating final recommendation: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {
            **state,
            "error": error_msg,
            "status": "error"
        }

def save_recommendation(state: GraphState) -> GraphState:
    """Save the recommendation to the database."""
    print("---NODE: Saving Recommendation---")
    recommendation = state.get("recommendation")
    
    if not recommendation:
        return {"error": "No recommendation to save"}
    
    try:
        # Save to database
        conn = sqlite3.connect("db/financial_advisor.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO recommendations 
            (user_id, recommendation_json, created_at)
            VALUES (?, ?, ?)
        """, (
            state["user_id"],
            json.dumps(recommendation),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        print("Recommendation saved successfully")
        return {"status": "recommendation_saved"}
        
    except Exception as e:
        print(f"Error saving recommendation: {str(e)}")
        return {"error": f"Failed to save recommendation: {str(e)}"}