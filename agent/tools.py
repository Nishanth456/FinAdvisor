import sqlite3
import json
from typing import Dict, Any, Optional, Type
from pathlib import Path
from pydantic import BaseModel, Field
from langchain.tools import BaseTool, tool

# Configuration
DB_PATH = "db/financial_advisor.db"
MARKET_DATA_PATH = "market_data.json"

# --- Tool 1: Get User Profile ---
class UserProfileInput(BaseModel):
    user_id: int = Field(description="The unique integer ID of the user.")

class UserProfileTool(BaseTool):
    name: str = "get_user_financial_profile"
    description: str = "Retrieves user profile and investment preferences from the database"
    args_schema: Type[BaseModel] = UserProfileInput
    
    def _run(self, user_id: int) -> Dict[str, Any]:
        """
        Fetches a user's complete financial profile from the database.
        Use this tool to get all necessary information about a user,
        such as their risk appetite, income, and financial goals.
        """
        print(f"🛠️ TOOL: Fetching profile for user_id: {user_id}")
        try:
            conn = sqlite3.connect(DB_PATH)
            # Use a dictionary cursor to get column names
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Query the user_profiles table using the provided user_id
            cursor.execute("""
                SELECT up.*, u.name, u.email 
                FROM user_profiles up
                JOIN users u ON up.user_id = u.id
                WHERE up.user_id = ?
            """, (user_id,))
            profile_row = cursor.fetchone()

            conn.close()

            if profile_row is None:
                return {"error": f"No profile found for user_id {user_id}"}

            # Convert the sqlite3.Row object to a standard dictionary
            profile_dict = dict(profile_row)
            
            # The 'financial_goals' are stored as a JSON string, so we parse it
            if 'financial_goals' in profile_dict and profile_dict['financial_goals']:
                try:
                    profile_dict['financial_goals'] = json.loads(profile_dict['financial_goals'])
                except json.JSONDecodeError:
                    profile_dict['financial_goals'] = []
                    
            print(f"✅ TOOL: Successfully fetched profile for user_id: {user_id}")
            return profile_dict

        except Exception as e:
            print(f"❌ TOOL ERROR in get_user_financial_profile: {e}")
            return {"error": f"An error occurred while fetching the user profile: {e}"}

# --- Tool 2: Get Market Data ---
class MarketDataTool(BaseTool):
    name: str = "get_market_data"
    description: str = "Retrieves current market data for all assets"
    
    
    def _run(self) -> Dict[str, Any]:
        """
        Fetches the latest mock market data from the market_data.json file.
        Use this tool to get information about available stocks, mutual funds,
        and fixed deposits, including their performance metrics.
        """
        print("🛠️ TOOL: Fetching market data...")
        try:
            with open(MARKET_DATA_PATH, 'r') as f:
                market_data = json.load(f)
            print("✅ TOOL: Successfully fetched market data.")
            return market_data
        except Exception as e:
            print(f"❌ TOOL ERROR in get_market_data: {e}")
            return {"error": f"An error occurred while fetching market data: {e}"}

# --- Tool 3: Get Portfolio Data ---
class PortfolioInput(BaseModel):
    user_id: int = Field(description="The unique integer ID of the user.")

class PortfolioTool(BaseTool):
    name: str = "get_user_portfolio"
    description: str = "Retrieves a user's investment portfolio"
    args_schema: Type[BaseModel] = PortfolioInput
    
    def _run(self, user_id: int) -> Dict[str, Any]:
        """
        Fetches a user's investment portfolio including all assets and their allocations.
        """
        print(f"🛠️ TOOL: Fetching portfolio for user_id: {user_id}")
        try:
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get user's portfolios
            cursor.execute("""
                SELECT p.id, p.name, p.description, p.target_allocation
                FROM portfolios p
                WHERE p.user_id = ?
            """, (user_id,))
            
            portfolios = []
            for row in cursor.fetchall():
                portfolio = dict(row)
                # Parse target_allocation if it exists
                if portfolio.get('target_allocation'):
                    try:
                        portfolio['target_allocation'] = json.loads(portfolio['target_allocation'])
                    except json.JSONDecodeError:
                        portfolio['target_allocation'] = {}
                portfolios.append(portfolio)

            conn.close()
            
            if not portfolios:
                return {"message": f"No portfolios found for user_id {user_id}", "portfolios": []}
                
            print(f"✅ TOOL: Successfully fetched {len(portfolios)} portfolios for user_id: {user_id}")
            return {"portfolios": portfolios}

        except Exception as e:
            print(f"❌ TOOL ERROR in get_user_portfolio: {e}")
            return {"error": f"An error occurred while fetching the portfolio: {e}"}

# Export tools for easy access
def get_all_tools():
    """Returns a list of all available tools."""
    return [
        UserProfileTool(),
        MarketDataTool(),
        PortfolioTool()
    ]
