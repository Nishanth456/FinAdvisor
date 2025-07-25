import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Literal

# Add the project root to Python path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

# Import the tools
from tools import get_all_tools

from functions import fetch_user_profile, calculate_savings, generate_fallback_recommendation
from functions import check_profile_completeness, fetch_market_data, preprocess_market_data, calculate_emergency_fund, analyze_goals_and_risk, define_risk_based_allocation
from functions import calculate_returns,generate_final_recommendation,save_recommendation

from selected_investments import select_investments

# Load environment variables from .env file
load_dotenv()

from models import GraphState, DEFAULT_ALLOCATIONS, RISK_PROFILES, ASSET_CLASSES

# Initialize the LLM and tools
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
tools = get_all_tools()
user_profile_tool = tools[0]  # UserProfileTool
market_data_tool = tools[1]   # MarketDataTool
portfolio_tool = tools[2]     # PortfolioTool


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

# Add all nodes
workflow.add_node("fetch_user_profile", fetch_user_profile)
workflow.add_node("check_profile_completeness", check_profile_completeness)
workflow.add_node("generate_fallback_recommendation", generate_fallback_recommendation)
workflow.add_node("fetch_market_data", fetch_market_data)
workflow.add_node("preprocess_market_data", preprocess_market_data)
workflow.add_node("calculate_emergency_fund", calculate_emergency_fund)
workflow.add_node("analyze_goals_and_risk", analyze_goals_and_risk)
workflow.add_node("define_risk_based_allocation", define_risk_based_allocation)
workflow.add_node("select_investment_products", select_investments)
workflow.add_node("calculate_returns", calculate_returns)
workflow.add_node("generate_final_recommendation", generate_final_recommendation)
workflow.add_node("save_recommendation", save_recommendation)

# Add error handling node
def handle_error(state: GraphState) -> Dict[str, Any]:
    """Handle any errors that occur during execution."""
    print("---NODE: Handling Error---")
    error_msg = state.get("error", "An unknown error occurred")
    print(f"Error: {error_msg}")
    
    return {
        **state,
        "recommendation": {
            "status": "error",
            "message": error_msg,
            "suggested_actions": [
                "Please try again later",
                "Contact support if the issue persists"
            ],
            "generated_at": datetime.now().isoformat(),
            "user_id": state.get("user_id")
        },
        "status": "error_handled"
    }
workflow.add_node("handle_error", handle_error)
workflow.add_edge("handle_error", END)

# Set the entry point
workflow.set_entry_point("fetch_user_profile")

# Define the graph edges with error handling
workflow.add_conditional_edges(
    "fetch_user_profile",
    lambda x: "check_profile_completeness" if x.get("status") != "error" else "handle_error"
)

workflow.add_conditional_edges(
    "check_profile_completeness",
    lambda x: x.get("status", "error"),
    {
        "profile_valid": "fetch_market_data",
        "profile_incomplete": "generate_fallback_recommendation",
        "profile_invalid": "generate_fallback_recommendation",
        "error": "handle_error"
    }
)

workflow.add_conditional_edges(
    "fetch_market_data",
    lambda x: "preprocess_market_data" if x.get("status") != "error" else "handle_error"
)

# Add conditional edges for the rest of the workflow
workflow.add_conditional_edges(
    "preprocess_market_data",
    lambda x: "calculate_emergency_fund" if x.get("status") == "market_data_processed" else "handle_error"
)

def route_after_emergency_fund(state: Dict[str, Any]) -> str:
    """Route to next node after calculating emergency fund."""
    if state.get("status") != "emergency_fund_calculated":
        return "handle_error"
    
    # Ensure the monthly investment is properly set in the state
    if "monthly_investment" not in state:
        state["monthly_investment"] = state.get("user_profile", {}).get("monthly_investment", 0)
    
    return "analyze_goals_and_risk"

workflow.add_conditional_edges(
    "calculate_emergency_fund",
    route_after_emergency_fund
)

workflow.add_conditional_edges(
    "analyze_goals_and_risk",
    lambda x: "define_risk_based_allocation" if x.get("status") == "risk_analyzed" else "handle_error"
)

workflow.add_conditional_edges(
    "define_risk_based_allocation",
    lambda x: "select_investment_products" if x.get("status") == "allocation_defined" else "handle_error"
)

workflow.add_conditional_edges(
    "select_investment_products",
    lambda x: "calculate_returns" if x.get("status") == "products_selected" else "handle_error"
)

workflow.add_conditional_edges(
    "calculate_returns",
    lambda x: "generate_final_recommendation" if x.get("status") == "returns_calculated" else "handle_error"
)

workflow.add_conditional_edges(
    "generate_final_recommendation",
    lambda x: "save_recommendation" if x.get("status") == "recommendation_generated" else "handle_error"
)

workflow.add_conditional_edges(
    "save_recommendation",
    lambda x: END if x.get("status") == "recommendation_saved" else "handle_error"
)

workflow.add_conditional_edges(
    "generate_fallback_recommendation",
    lambda x: END if x.get("status") == "completed_with_fallback" else "handle_error"
)

# Compile the graph
app = workflow.compile()

# --- 4. Example Usage ---
if __name__ == "__main__":
    print("🚀 Running Financial Advisor Agent with Gemini...")
    
    user_id = 16  # Or get this from user input/authentication
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