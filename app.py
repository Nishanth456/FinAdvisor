import sys
import os
from pathlib import Path
import json
import sqlite3
import bcrypt
from jose import jwt as PyJWT
from jose.exceptions import JWTError
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = str(Path(__file__).resolve().parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the compiled agent app
from agent.financial_agent import app as financial_agent_app

# --- Constants ---
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
DB_PATH = "db/financial_advisor.db"


from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic Models ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

    @validator('password')
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class UserInDB(UserBase):
    id: int
    is_active: bool = True

class UserProfileCreate(BaseModel):
    date_of_birth: str
    monthly_income: float = Field(..., gt=0, description="Monthly income should be greater than 0")
    monthly_expenses: float = Field(..., ge=0, description="Monthly expenses should be 0 or more")
    risk_appetite: str = Field(..., description="Risk appetite level (any value is accepted)")
    investment_horizon_years: int = Field(..., gt=0)
    financial_goals: List[str]

# --- Database Setup ---
def init_db():
    """Initialize database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create user_profiles table without risk_appetite constraints
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,
        date_of_birth TEXT NOT NULL,
        monthly_income REAL NOT NULL,
        monthly_expenses REAL NOT NULL,
        risk_appetite TEXT NOT NULL,
        investment_horizon_years INTEGER NOT NULL,
        financial_goals TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()



# Initialize database on startup
init_db()

# --- Database Helpers ---
def get_db_connection():
    """Get a database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_by_email(email: str):
    """Get a user by email."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(user: UserCreate):
    """Create a new user in the database."""
    print(f"Creating user: {user.email}")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hash the password
        print("Hashing password...")
        hashed_password = get_password_hash(user.password)
        
        # Insert the new user
        print("Executing SQL insert...")
        cursor.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            (user.name, user.email, hashed_password)
        )
        
        user_id = cursor.lastrowid
        print(f"User inserted with ID: {user_id}")
        
        conn.commit()
        print("Transaction committed successfully")
        return user_id
        
    except sqlite3.IntegrityError as e:
        print(f"IntegrityError: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    except sqlite3.Error as e:
        print(f"SQLite error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error in create_user: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )
    finally:
        if conn:
            conn.close()

def get_user(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        if user:
            return dict(user)
        return None
    except Exception as e:
        print(f"Error getting user: {str(e)}")
        return None
    finally:
        conn.close()

def update_db_schema():
    """Update database schema if needed."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check if is_active column exists in users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add is_active column if it doesn't exist
        if "is_active" not in columns:
            print("Adding is_active column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
            conn.commit()
            
    except Exception as e:
        print(f"Error updating database schema: {e}")
        conn.rollback()
    finally:
        conn.close()

update_db_schema()

# --- Security Utils ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        print(f"Password verification error: {e}")  # Debug log
        return False

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = PyJWT.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- FastAPI App Setup ---
app = FastAPI(
    title="Smart Financial Advisor API",
    description="API for user management and personalized investment recommendations.",
    version="1.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:5173"],  # Add both React dev server ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Dependency Injections ---
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = PyJWT.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

# --- API Endpoints ---
@app.post("/api/recommendations/generate", response_model=Dict[str, Any])
async def generate_financial_recommendation(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Generate new financial recommendations for the current user"""
    try:
        # Generate new recommendations
        final_state = financial_agent_app.invoke({"user_id": current_user['id']})
        
        if "recommendation" not in final_state:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=final_state.get("error", "Failed to generate recommendation")
            )
        
        recommendation_data = final_state["recommendation"]
        
        # Save the recommendation to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO recommendations (user_id, recommendation_json)
            VALUES (?, ?)
        ''', (
            current_user['id'],
            json.dumps(recommendation_data)
        ))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "data": recommendation_data}
        
    except Exception as e:
        print(f"Error in generate_financial_recommendation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/recommendations", response_model=Dict[str, Any])
async def get_financial_recommendation(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get existing financial recommendations for the current user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get the most recent recommendation for the user
        cursor.execute('''
            SELECT id, user_id, recommendation_json, created_at 
            FROM recommendations 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (current_user['id'],))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                # Parse the JSON data
                recommendation_data = json.loads(row['recommendation_json'])
                return {
                    "success": True, 
                    "data": recommendation_data,
                    "created_at": row['created_at']
                }
            except json.JSONDecodeError as e:
                print(f"Error parsing recommendation JSON: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to parse recommendation data"
                )
        else:
            return {
                "success": False,
                "message": "No recommendations found. Please generate recommendations first."
            }
            
    except Exception as e:
        print(f"Error in get_financial_recommendation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/signup")
async def signup(user: UserCreate):
    """Handle user signup"""
    try:
        print(f"Starting signup for email: {user.email}")
        
        # Check if user already exists
        print("Checking if user exists...")
        existing_user = get_user_by_email(user.email)
        if existing_user:
            print(f"User with email {user.email} already exists")
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )
        
        # Create new user
        print("Creating new user...")
        try:
            user_id = create_user(user)
            print(f"User created successfully with ID: {user_id}")
        except Exception as e:
            print(f"Error in create_user: {str(e)}")
            raise
        
        # Generate token
        print("Generating access token...")
        try:
            access_token = create_access_token(
                data={"sub": user.email}  # Using email as subject for JWT
            )
            print("Access token generated successfully")
        except Exception as e:
            print(f"Error generating access token: {str(e)}")
            raise
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id
        }
        
    except HTTPException as he:
        print(f"HTTPException in signup: {str(he.detail)}")
        raise
    except Exception as e:
        print(f"Unexpected error in signup: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during signup: {str(e)}"
        )

@app.get("/users/me", response_model=Dict[str, Any])
async def read_users_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user information."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM user_profiles WHERE user_id = ?",
            (current_user['id'],)
        )
        profile = cursor.fetchone()
        
        user_data = {
            "id": current_user['id'],
            "name": current_user['name'],
            "email": current_user['email'],
            "has_profile": profile is not None
        }
        
        if profile:
            user_data["profile"] = {
                "date_of_birth": profile[1],
                "monthly_income": profile[2],
                "monthly_expenses": profile[3],
                "risk_appetite": profile[4],
                "investment_horizon_years": profile[5],
                "financial_goals": json.loads(profile[6]) if profile[6] else []
            }
            
        return user_data
    finally:
        conn.close()

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 compatible token login, get an access token for future requests."""
    print(f"Login attempt for email: {form_data.username}")  # Debug log
    user = get_user(form_data.username)
    if not user:
        print("User not found")  # Debug log
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(form_data.password, user["password_hash"]):
        print("Invalid password")  # Debug log
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/check-email")
async def check_email_exists(email: str):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        return {"exists": user is not None}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/users/me/profile")
async def create_update_profile(
    profile: UserProfileCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Create or update user profile."""
    print(f"Received profile update request for user_id: {current_user['id']}")
    print(f"Profile data: {profile.dict()}")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Validate the user exists
        cursor.execute("SELECT id FROM users WHERE id = ?", (current_user['id'],))
        if not cursor.fetchone():
            print(f"User not found: {current_user['id']}")
            raise HTTPException(
                status_code=404,
                detail="User not found. Please log in again."
            )
        
        # Convert financial_goals list to a JSON string
        try:
            financial_goals_json = json.dumps(profile.financial_goals)
            print(f"Formatted financial goals: {financial_goals_json}")
        except Exception as e:
            error_msg = f"Invalid financial goals format: {str(e)}"
            print(error_msg)
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )
        
        # Check if profile already exists
        cursor.execute(
            "SELECT 1 FROM user_profiles WHERE user_id = ?",
            (current_user['id'],)
        )
        profile_exists = cursor.fetchone() is not None
        print(f"Profile exists: {profile_exists}")
        
        try:
            if profile_exists:
                print("Updating existing profile...")
                # Update existing profile
                cursor.execute("""
                    UPDATE user_profiles 
                    SET date_of_birth = ?, 
                        monthly_income = ?, 
                        monthly_expenses = ?, 
                        risk_appetite = ?,
                        investment_horizon_years = ?, 
                        financial_goals = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (
                    profile.date_of_birth,
                    float(profile.monthly_income),
                    float(profile.monthly_expenses),
                    profile.risk_appetite,  # Already validated by Pydantic
                    int(profile.investment_horizon_years),
                    financial_goals_json,
                    current_user['id']
                ))
                print("Profile update query executed")
            else:
                print("Creating new profile...")
                # Create new profile
                cursor.execute("""
                    INSERT INTO user_profiles 
                    (user_id, date_of_birth, monthly_income, monthly_expenses,risk_appetite, investment_horizon_years, financial_goals)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    current_user['id'],
                    profile.date_of_birth,
                    float(profile.monthly_income),
                    float(profile.monthly_expenses),
                    profile.risk_appetite,  # Already validated by Pydantic
                    int(profile.investment_horizon_years),
                    financial_goals_json
                ))
                print("Profile insert query executed")
            
            conn.commit()
            print("Transaction committed successfully")
            return {"message": "Profile updated successfully", "profile_updated": True}
            
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            error_detail = f"Database error: {str(e)}"
            if "UNIQUE constraint failed" in str(e):
                error_detail = "A profile already exists for this user"
            elif "FOREIGN KEY constraint failed" in str(e):
                error_detail = "Invalid user reference. Please log in again."
            
            print(f"Database error: {error_detail}")
            print(f"SQLite error: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=error_detail
            )
            
    except HTTPException as he:
        print(f"HTTPException occurred: {he.detail}")
        raise
    except Exception as e:
        print(f"Unexpected error in create_update_profile: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while processing your request: {str(e)}"
        )
    finally:
        if conn:
            try:
                conn.close()
                print("Database connection closed")
            except Exception as e:
                print(f"Error closing database connection: {str(e)}")
            conn.close()

@app.get("/users/me/recommendations")
async def get_recommendations(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get the most recent recommendations for the current user from the database.
    
    Returns the most recent recommendation if it exists, otherwise returns an empty response.
    """
    try:
        from agent.financial_agent import get_user_recommendations
        existing_recs = get_user_recommendations(current_user['id'], limit=1)
        
        if existing_recs and len(existing_recs) > 0:
            # Return the most recent recommendation
            return existing_recs[0]['recommendation_json']
            
        # If no recommendations exist, return an empty response
        return {
            "message": "No recommendations found. Please generate recommendations first.",
            "recommendations": []
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "message": "Service is running"}

# Test endpoint
@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify backend is accessible."""
    return {"status": "success", "message": "Backend is accessible"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Smart Financial Advisor API",
        "version": "1.1.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)