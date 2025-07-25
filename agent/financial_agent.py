import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, TypedDict, Optional

# Add the project root to Python path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv

# Import the tools
from tools import get_all_tools

# Load environment variables from .env file
load_dotenv()

# --- 1. Define the State for our Graph ---
class GraphState(TypedDict):
    user_id: int
    user_profile: Optional[Dict[str, Any]]
    market_data: Optional[Dict[str, Any]]
    recommendation: Optional[Dict[str, Any]]
    error: Optional[str]

# Initialize the LLM and tools
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
tools = get_all_tools()
user_profile_tool = tools[0]  # UserProfileTool
market_data_tool = tools[1]   # MarketDataTool
portfolio_tool = tools[2]     # PortfolioTool

# --- 2. Define the Agent Nodes ---
def fetch_user_profile(state: GraphState):
    """Node to fetch user profile."""
    print("---NODE: Fetching User Profile---")
    try:
        data = user_profile_tool._run(state["user_id"])
        if "error" in data:
            print(f"ERROR: {data['error']}")
            return {"error": data['error']}
        return {"user_profile": data}
    except Exception as e:
        print(f"Error fetching user profile: {e}")
        return {"error": str(e)}

def fetch_market_data(state: GraphState):
    """Node to fetch market data."""
    print("---NODE: Fetching Market Data---")
    try:
        data = market_data_tool._run()
        if "error" in data:
            print(f"ERROR: {data['error']}")
            return {"error": data['error']}
        return {"market_data": data}
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return {"error": str(e)}

# Define the output structure for the LLM
class Recommendation(BaseModel):
    allocation_summary: Dict[str, str] = Field(
        ...,
        description="A dictionary with asset classes as keys and their recommended allocation percentages as values."
    )
    suggested_instruments: Dict[str, List[Dict[str, Any]]] = Field(
        ...,
        description="A dictionary with asset classes as keys and lists of recommended instruments as values."
    )
    explanation: str = Field(
        ...,
        description="A brief explanation of why this allocation fits the user's risk profile and financial goals."
    )
    projected_returns_text: str = Field(
        ...,
        description="A simple narrative about potential returns."
    )
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    user_id: int = Field(..., description="The ID of the user this recommendation is for")

def generate_recommendation(state: GraphState):
    """Node to generate the investment recommendation based on the user's profile."""
    print("---NODE: Generating Recommendation---")
    profile = state['user_profile']
    market = state['market_data']
    
    risk_appetite = profile.get("risk_appetite", "Medium")
    
    # Define the allocation based on risk profile
    allocations = {
        "Low": {"stocks": "10%", "mutual_funds": "40%", "fixed_deposits": "50%"},
        "Medium": {"stocks": "40%", "mutual_funds": "40%", "fixed_deposits": "20%"},
        "High": {"stocks": "70%", "mutual_funds": "25%", "fixed_deposits": "5%"}
    }
    
    chosen_allocation = allocations.get(risk_appetite, allocations["Medium"])

    # Create the prompt with explicit instructions for JSON output
    prompt = ChatPromptTemplate.from_messages([

    ("system", """You are a financial advisor providing investment recommendations.

        You MUST respond with a valid JSON object that matches this schema:

        {{
            "allocation_summary": {{
                "stocks": "string (percentage with % sign)",
                "mutual_funds": "string (percentage with % sign)",
                "fixed_deposits": "string (percentage with % sign)"
            }},

            "suggested_instruments": {{
                "stocks": [
                    {{
                        "symbol": "SYM001",
                        "name": "Company Name",
                        "sector": "Sector Name",
                        "growth_pct_yoy": 0.0
                    }}
                ],
                "mutual_funds": [
                    {{
                        "code": "MF_XXX_XXX",
                        "name": "Fund Name",
                        "category": "Category",
                        "return_pct_3y_cagr": 0.0
                    }}
                ],
                "fixed_deposits": [
                    {{
                        "bank": "Bank Name",
                        "tenure_months": 12,
                        "rate_pct": 0.0
                    }}
                ]
            }},

            "investment_plan": {{
                "monthly_investment": "₹X",
                "emergency_fund": "₹X",

                // emergency_fund = 5% of (monthly_income - monthly_expenses)
                // monthly_investment = (monthly_income - monthly_expenses) - emergency_fund

                "goal_breakdown": {{
                    "goal_1": {{"name": "Goal Name", "amount": "₹X", "strategy": "..."}},
                    "goal_2": {{"name": "Goal Name", "amount": "₹X", "strategy": "..."}},
                    ...(until all goals are covered)

                    // Divide investment goal amounts into short-term vs long-term
                    // Use FDs for short-term, mutual funds or stocks for long-term
                    // Suggest strategies like SIP, lump sum, etc.
                }},

                "risk_management": ["...", "..."]

                // Examples: diversification, SIPs, low-volatility instruments, etc.
                // Match suggestions based on risk appetite
            }},

            "explanation": "Detailed explanation...",

            "projected_returns": {{
                "conservative": "X% CAGR",
                "moderate": "X% CAGR",
                "aggressive": "X% CAGR",

                "expected_value for stocks": "₹X in Y years",
                "expected_value for mutual funds": "₹X in Y years",
                "expected_value for fixed deposits": "₹X in Y years",
                "total expected_value": "₹X in Y years"
            }}
        }}

        IMPORTANT:

        1. For each instrument in suggested_instruments, include the full object with all its properties.

        2. Only suggest instruments that exist in the provided market data.

        3. DO NOT pick instruments randomly. Select instruments **intelligently** based on:
            - User's financial goals and timelines
            - Risk appetite (conservative/moderate/aggressive)
            - Monthly investment and allocation percentages
            - Preference for return type (growth/safety)

        4. Instrument selection logic:
            - Stocks: choose 2 companies with highest `growth_pct_yoy`
            - Mutual Funds: pick 2 with highest `return_pct_3y_cagr`
            - Fixed Deposits: pick 2 with highest `rate_pct`
            - All instruments MUST come from the provided market_data.

        5. Monthly Investment:
            - Calculate as: `monthly_income - monthly_expenses`
            - Then deduct 5% of that value as emergency fund
            - Final investment amount = 95% of (monthly_income - expenses)

        6. Emergency Fund:
            - Compute and include in output as a separate field
            - Value = 5% of (monthly_income - monthly_expenses)

        7. Projected Returns:
            - Use compound interest formula: A = P * (1 + r)^t
                - P = (monthly_investment × allocation %) * 12 
                - r = average return of selected instruments for each category
                - t = duration (Y years, inferred from user's goals)
            - Provide expected_value for each category
            - Sum them for total expected_value
        """),

        ("human", """User Profile:

        {profile}

        Market Data:

        {market_data}

        Risk Appetite: {risk_appetite}
        Recommended Allocation: {allocation}

        Please provide a personalized investment recommendation in the exact JSON format specified above.

        - For suggested_instruments, pick 2 items from each category in the market data.
        - Keep the explanation brief and professional.
        - The projected_returns_text should be a simple narrative.
        """)
    ])



    try:
        # Format the market data to be more concise
        formatted_market = {
            "stocks": market.get("stocks", [])[:5],  # Return full stock objects
            "mutual_funds": market.get("mutual_funds", [])[:5],  # Return full fund objects
            "fixed_deposits": market.get("fixed_deposits", [])[:5]  # Return full FD objects
        }

        # Get the response from the LLM
        chain = prompt | llm
        response = chain.invoke({
            "profile": json.dumps(profile, indent=2),
            "market_data": json.dumps(formatted_market, indent=2),
            "risk_appetite": risk_appetite,
            "allocation": json.dumps(chosen_allocation, indent=2)
        })

        # Parse the response
        # After getting the response from the LLM
        try:
            # Extract JSON from the response content
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if not json_match:
                raise ValueError("Could not parse JSON from response")
                
            recommendation = json.loads(json_match.group(0))
            recommendation['user_id'] = state['user_id']
            
            # Validate the structure
            if 'suggested_instruments' not in recommendation:
                recommendation['suggested_instruments'] = {
                    'stocks': [],
                    'mutual_funds': [],
                    'fixed_deposits': []
                }
            
            # No need for get_instrument_details anymore
            # Just ensure each instrument has the required fields
            for inst_type in ['stocks', 'mutual_funds', 'fixed_deposits']:
                if inst_type not in recommendation['suggested_instruments']:
                    recommendation['suggested_instruments'][inst_type] = []
            
            # Save to database
            if save_recommendation_to_db(recommendation):
                print("✅ Recommendation saved to database")
            else:
                print("⚠️ Could not save recommendation to database")
            
            return {"recommendation": recommendation}
            
        except Exception as e:
            print(f"❌ Error parsing LLM response: {e}")
            raise ValueError("Failed to parse LLM response into the required format")

    except Exception as e:
        print(f"❌ Error in generate_recommendation: {e}")
        return {"error": f"Failed to generate recommendation: {e}"}

def save_recommendation_to_db(recommendation: Dict[str, Any]) -> bool:
    """Save recommendation to SQLite database."""
    conn = None
    try:
        conn = sqlite3.connect('db/financial_advisor.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO recommendations (user_id, recommendation_json, created_at)
        VALUES (?, ?, ?)
        ''', (
            recommendation['user_id'],
            json.dumps(recommendation),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving recommendation to database: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_user_recommendations(user_id: int, limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch user's past recommendations from the database."""
    conn = None
    try:
        conn = sqlite3.connect('db/financial_advisor.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, user_id, recommendation_json, created_at 
        FROM recommendations 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
        ''', (user_id, limit))
        
        results = []
        for row in cursor.fetchall():
            rec = dict(row)
            rec['recommendation_json'] = json.loads(rec['recommendation_json'])
            results.append(rec)
        return results
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
        return []
    finally:
        if conn:
            conn.close()

# --- 3. Build the Graph ---
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("fetch_user_profile", fetch_user_profile)
workflow.add_node("fetch_market_data", fetch_market_data)
workflow.add_node("generate_recommendation", generate_recommendation)

# Define the edges
workflow.add_edge(START, "fetch_user_profile")
workflow.add_edge("fetch_user_profile", "fetch_market_data")
workflow.add_edge("fetch_market_data", "generate_recommendation")
workflow.add_edge("generate_recommendation", END)

# Set the entry point
workflow.set_entry_point("fetch_user_profile")

# Compile the workflow
app = workflow.compile()

# --- 4. Example Usage ---
if __name__ == "__main__":
    print("🚀 Running Financial Advisor Agent with Gemini...")
    
    user_id = 2  # Or get this from user input/authentication
    inputs = {"user_id": user_id}
    
    try:
        # Check for existing recommendations first
        existing_recs = get_user_recommendations(user_id, limit=1)
        if existing_recs:
            print("\n📊 Found existing recommendation")
            print("="*50)
            print(json.dumps(existing_recs[0]["recommendation_json"], indent=2))
            print("="*50)
            
            use_existing = input("\nUse this recommendation? (y/n): ").lower() == 'y'
            if use_existing:
                print("Using existing recommendation")
                final_state = {"recommendation": existing_recs[0]["recommendation_json"]}
            else:
                print("Generating new recommendation...")
                final_state = app.invoke(inputs)
        else:
            print("No existing recommendations found. Generating new one...")
            final_state = app.invoke(inputs)
        
        # Display the final recommendation
        if "recommendation" in final_state and final_state.get("recommendation"):
            print("\n" + "="*50)
            print("✅ FINAL RECOMMENDATION")
            print("="*50)
            print(json.dumps(final_state["recommendation"], indent=2))
            print("="*50 + "\n")
        else:
            print("❌ Failed to generate recommendation")
            if "error" in final_state:
                print(f"Error: {final_state['error']}")
                
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")