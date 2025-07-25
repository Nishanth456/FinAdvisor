from typing import Dict, Any, Optional, Tuple
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os
import json
import re
import sqlite3
from pathlib import Path

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "financial_advisor.db")
MARKET_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "market_data.json")

# Load environment variables
load_dotenv()

# Initialize the LLM
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)

def load_market_data(file_path: Optional[str] = None) -> Dict[str, Any]:
    """Load market data from JSON file."""
    if file_path is None:
        file_path = MARKET_DATA_PATH
    
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to load market data from {file_path}: {str(e)}")

def select_investments(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Select investment products based on user profile and market data.
    This version is compatible with the workflow state.
    """
    print("=== Starting select_investments ===")
    try:
        # Extract data from state
        print("Debug - State keys:", list(state.keys()))
        profile = state.get('profile', {})
        market_data = state.get('market_data', {})
        
        print(f"Debug - Profile keys: {list(profile.keys())}")
        print(f"Debug - Market data keys: {list(market_data.keys()) if isinstance(market_data, dict) else 'Not a dict'}")
        
        if not market_data:
            raise ValueError("No market data available in state")
            
        # Get risk appetite from profile, state, or asset_allocation
        risk_appetite = (
            profile.get("risk_appetite") or 
            state.get("risk_appetite") or 
            state.get("asset_allocation", {}).get("risk_profile", "medium")
        )
        
        # Normalize risk profile (handle both lowercase and capitalized)
        risk_appetite = str(risk_appetite).lower()
        if risk_appetite == "medium":
            risk_appetite = "Medium"
        else:
            risk_appetite = risk_appetite.capitalize()
        
        # Validate risk profile
        valid_risk_profiles = ["Low", "Medium", "High"]
        if risk_appetite not in valid_risk_profiles:
            print(f"Warning: Invalid risk profile '{risk_appetite}'. Using 'Medium' as default.")
            risk_appetite = "Medium"
        
        print(f"Using risk profile: {risk_appetite}")
        
        # Check if we have an allocation from the state
        if "asset_allocation" in state and isinstance(state["asset_allocation"], dict):
            allocation = state["asset_allocation"]
            print(f"Debug - Raw asset_allocation: {allocation}")
            
            # Try to extract the allocation values
            try:
                chosen_allocation = {}
                
                # First try the new format (equity/fixed_income/cash)
                if all(k in allocation for k in ["equity", "fixed_income", "cash"]):
                    # Map equity/fixed_income/cash to stocks/mutual_funds/fixed_deposits
                    chosen_allocation = {
                        "stocks": allocation["equity"],
                        "mutual_funds": allocation["fixed_income"],
                        "fixed_deposits": allocation["cash"]
                    }
                    print("Mapped allocation from equity/fixed_income/cash format")
                else:
                    # Fall back to old format (stocks/mutual_funds/fixed_deposits)
                    for asset_type in ["stocks", "mutual_funds", "fixed_deposits"]:
                        if asset_type in allocation:
                            value = allocation[asset_type]
                            if isinstance(value, str):
                                # Handle percentage strings (e.g., "40%" -> 0.4)
                                if '%' in value:
                                    chosen_allocation[asset_type] = float(value.strip('%')) / 100
                                else:
                                    chosen_allocation[asset_type] = float(value)
                            elif isinstance(value, (int, float)):
                                # If it's already a number, use it as is
                                chosen_allocation[asset_type] = float(value)
                
                # If we still don't have any allocations, raise an error
                if not chosen_allocation:
                    raise ValueError("No valid allocation values found in asset_allocation")
                
                # Convert all values to float to ensure consistency
                chosen_allocation = {k: float(v) for k, v in chosen_allocation.items()}
                print(f"Using allocation: {chosen_allocation}")
                
            except Exception as e:
                print(f"Warning: Error processing asset_allocation: {str(e)}")
                print("Falling back to default allocation")
                chosen_allocation = None
        
        # If we don't have a valid allocation yet, use defaults
        if not chosen_allocation:
            # Fallback to default allocations
            allocations = {
                "Low": {"stocks": 0.1, "mutual_funds": 0.4, "fixed_deposits": 0.5},
                "Medium": {"stocks": 0.4, "mutual_funds": 0.4, "fixed_deposits": 0.2},
                "High": {"stocks": 0.7, "mutual_funds": 0.25, "fixed_deposits": 0.05}
            }
            chosen_allocation = allocations.get(risk_appetite, allocations["Medium"])
            print(f"Using default allocation for {risk_appetite} risk: {chosen_allocation}")
        
        # Ensure all required asset types are present
        for asset_type in ["stocks", "mutual_funds", "fixed_deposits"]:
            if asset_type not in chosen_allocation:
                chosen_allocation[asset_type] = 0.0
                print(f"Warning: Missing {asset_type} in allocation, defaulting to 0.0")
        
        print(f"Final allocation: {chosen_allocation}")
        
        # Prepare the system prompt with properly escaped JSON
        try:
            print("Debug - Preparing system prompt...")
            system_prompt = """
            You are a financial advisor selecting investment products.
            Based on the user profile and market data, suggest specific investment products.
            
            User Profile:
            {profile}
            
            Market Data:
            {market_data}
            
            Risk Appetite: {risk_appetite}
            Target Allocation: {allocation}
            
            Return a JSON object with a single key 'suggested_instruments' containing three arrays:
            1. 'stocks' - List of stock recommendations
            2. 'mutual_funds' - List of mutual fund recommendations
            3. 'fixed_deposits' - List of fixed deposit options
            
            Each recommendation should include at least 'name' and 'allocation_percentage'.
            The sum of allocation percentages for each category should be close to 100%.
            
            Example:
            {{
                "suggested_instruments": {{
                    "stocks": [
                        {{"name": "Company A", "allocation_percentage": 40.0, "reason": "Strong growth potential"}},
                        {{"name": "Company B", "allocation_percentage": 30.0, "reason": "Stable dividends"}}
                    ],
                    "mutual_funds": [
                        {{"name": "Fund X", "allocation_percentage": 30.0, "reason": "Diversified portfolio"}}
                    ],
                    "fixed_deposits": []
                }}
            }}
            
            Only return the JSON object, no other text or explanation.
            """
            print("Debug - System prompt prepared")
        except Exception as e:
            print(f"Error preparing system prompt: {str(e)}")
            raise

        human_prompt = """
        User Profile:
        {profile}

        Market Data:
        {market_data}

        Risk Appetite: {risk_appetite}
        Recommended Allocation: {allocation}

        Please provide investment instruments in the exact JSON format specified above.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt.strip()),
            ("human", human_prompt.strip())
        ])

        # Format the market data for the prompt
        formatted_market = {
            "stocks": market_data.get("stocks", [])[:10],
            "mutual_funds": market_data.get("mutual_funds", [])[:10],
            "fixed_deposits": market_data.get("fixed_deposits", [])[:10]
        }

        # Get the response from the LLM
        try:
            print("Debug - Creating LLM chain...")
            chain = prompt | llm
            
            # Prepare inputs
            profile_json = json.dumps(profile, indent=2, default=str)
            market_json = json.dumps(formatted_market, indent=2, default=str)
            allocation_json = json.dumps(chosen_allocation, indent=2, default=str)
            
            print("Debug - Invoking LLM chain...")
            response = chain.invoke({
                "profile": profile_json,
                "market_data": market_json,
                "risk_appetite": risk_appetite,
                "allocation": allocation_json
            })
            print("Debug - LLM response received")
            print(f"Debug - Response type: {type(response)}")
            print(f"Debug - Response content: {response}")
            
        except Exception as e:
            print(f"Error invoking LLM chain: {str(e)}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            raise

        # Extract and parse the JSON response
        try:
            print("Debug - Processing LLM response...")
            
            # Handle different response types
            if hasattr(response, 'content'):
                content = response.content
            elif isinstance(response, str):
                content = response
            elif hasattr(response, 'text'):
                content = response.text
            else:
                content = str(response)
                
            print(f"Debug - Raw response content: {content[:500]}...")  # Print first 500 chars
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                print("Warning: No JSON found in response, using empty result")
                result = {'suggested_instruments': {'stocks': [], 'mutual_funds': [], 'fixed_deposits': []}}
            else:
                response_json = json_match.group(0)
                print(f"Debug - Extracted JSON: {response_json[:500]}...")  # Print first 500 chars
                result = json.loads(response_json)
            
            # Ensure the response has the expected structure
            if 'suggested_instruments' not in result:
                print("Warning: 'suggested_instruments' not in response, creating empty structure")
                result['suggested_instruments'] = {
                    'stocks': [],
                    'mutual_funds': [],
                    'fixed_deposits': []
                }
                
            # Ensure all required keys exist
            for inst_type in ['stocks', 'mutual_funds', 'fixed_deposits']:
                if inst_type not in result['suggested_instruments']:
                    print(f"Warning: '{inst_type}' not in suggested_instruments, adding empty list")
                    result['suggested_instruments'][inst_type] = []
                    
            print("Debug - Processed response structure:", 
                 {k: f"list[{len(v)} items]" for k, v in result['suggested_instruments'].items()})
                    
        except json.JSONDecodeError as je:
            print(f"JSON decode error: {str(je)}")
            print(f"Problematic content: {content[:500]}...")
            result = {'suggested_instruments': {'stocks': [], 'mutual_funds': [], 'fixed_deposits': []}}
        except Exception as e:
            print(f"Error processing response: {str(e)}")
            import traceback
            print(f"Error details: {traceback.format_exc()}")
            result = {'suggested_instruments': {'stocks': [], 'mutual_funds': [], 'fixed_deposits': []}}
        
        # Prepare the updated state with all necessary fields
        updated_state = {
            **state,
            "suggested_instruments": result['suggested_instruments'],
            "selected_products": {  # Also populate selected_products for backward compatibility
                "stocks": result['suggested_instruments'].get('stocks', []),
                "mutual_funds": result['suggested_instruments'].get('mutual_funds', []),
                "fixed_deposits": result['suggested_instruments'].get('fixed_deposits', []),
                "total_allocated": 0  # Will be calculated in generate_final_recommendation
            },
            "status": "products_selected"  # This matches what the workflow expects
        }
        
        print(f"Debug - Updated state keys: {list(updated_state.keys())}")
        if 'suggested_instruments' in updated_state:
            print(f"Debug - suggested_instruments keys: {list(updated_state['suggested_instruments'].keys())}")
        if 'selected_products' in updated_state:
            print(f"Debug - selected_products keys: {list(updated_state['selected_products'].keys())}")
            
        return updated_state
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in select_investments: {str(e)}")
        print(f"Error details: {error_trace}")
        
        # Log the state for debugging (without sensitive data)
        debug_state = {
            k: v for k, v in state.items() 
            if k not in ['profile', 'market_data'] and not k.startswith('_')
        }
        print(f"Debug - Current state keys: {list(state.keys())}")
        print(f"Debug - State preview: {debug_state}")
        
        # Return the state with error information
        return {
            **state,
            "error": f"Error selecting investments: {str(e)}",
            "error_details": error_trace,
            "suggested_instruments": {
                "stocks": [],
                "mutual_funds": [],
                "fixed_deposits": []
            },
            "status": "error"
        }

def get_user_profile(db_path: str, user_id: int) -> Dict[str, Any]:
    """Fetch user profile from the database or return a default profile if not found."""
    # Default profile in case of any errors
    default_profile = {
        "user_id": user_id,
        "name": f"User {user_id}",
        "monthly_income": 100000,
        "monthly_expenses": 60000,
        "risk_appetite": "Medium",
        "investment_horizon_years": 5
    }
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Warning: Database file not found at {db_path}. Using default profile.")
        return default_profile
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First check if the user_profiles table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_profiles';")
        if not cursor.fetchone():
            print("Warning: 'user_profiles' table not found in the database. Using default profile.")
            return default_profile
        
        # Query to get user details based on user_id
        cursor.execute("""
            SELECT user_id, date_of_birth, monthly_income, monthly_expenses,
                   risk_appetite, investment_horizon_years, financial_goals
            FROM user_profiles 
            WHERE user_id = ?
        """, (user_id,))
        
        user_data = cursor.fetchone()
        
        if not user_data:
            print(f"Warning: User with ID {user_id} not found in the database. Using default profile.")
            return default_profile
        
        # Map the database row to a dictionary
        profile = {
            "user_id": user_data[0],
            "date_of_birth": user_data[1],
            "monthly_income": float(user_data[2]) if user_data[2] is not None else 0,
            "monthly_expenses": float(user_data[3]) if user_data[3] is not None else 0,
            "risk_appetite": user_data[4] or "Medium",
            "investment_horizon_years": int(user_data[5]) if user_data[5] is not None else 5,
            "financial_goals": user_data[6] or ""
        }
        
        return profile
        
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}. Using default profile.")
        return default_profile
    except Exception as e:
        print(f"Error: {str(e)}. Using default profile.")
        return default_profile
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    try:
        # Ensure the db directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Get user profile from database
        print(f"Fetching user profile from: {DB_PATH}")
        user_profile = get_user_profile(DB_PATH, user_id=16)
        
        # Create a display name from user ID if name is not available
        display_name = user_profile.get('name', f"User {user_profile['user_id']}")
        print(f"Found user: {display_name}")
        
        # Get investment recommendations using the user profile from database
        print(f"Loading market data from: {MARKET_DATA_PATH}")
        investments = select_investments(user_profile, MARKET_DATA_PATH)
        
        print("\n=== Investment Recommendation ===")
        print(f"User ID: {user_profile['user_id']}")
        if 'date_of_birth' in user_profile and user_profile['date_of_birth']:
            print(f"Date of Birth: {user_profile['date_of_birth']}")
        print(f"Risk Appetite: {user_profile['risk_appetite']}")
        if 'financial_goals' in user_profile and user_profile['financial_goals']:
            print(f"Financial Goals: {user_profile['financial_goals']}")
        print("\nRecommended Investments:")
        print(json.dumps(investments, indent=2))
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
