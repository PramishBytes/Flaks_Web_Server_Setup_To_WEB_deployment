from flask import Flask, jsonify, request
import sqlite3
import hashlib
import os
from functools import wraps
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

# Configuration
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    print("WARNING: API_TOKEN not set in environment variables!")

app = Flask(__name__)

# Database configuration
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "products.db")

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def require_token(f):
    """Decorator to require a valid Bearer token for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        
        # Check if Authorization header exists and has correct format
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        
        # Extract token from "Bearer <token>"
        token = auth_header.split(" ")[1]
        
        # Validate token
        if token != API_TOKEN:
            return jsonify({"error": "Invalid API token"}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

@app.route("/init", methods=["GET"])
def init_db():
    """Initialize database with required tables."""
    try:
        conn = get_db_connection()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        return jsonify({"message": "Database initialized successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Database initialization failed: {str(e)}"}), 500

@app.route("/")
def home():
    """Home endpoint."""
    return jsonify({
        "message": "Welcome to the Product API",
        "endpoints": {
            "/init": "Initialize database (GET)",
            "/products": "Get all products (GET) or Add product (POST - requires token)",
            "/register": "Register new user (POST)",
            "/login": "Login user (POST)"
        }
    })

@app.route("/products", methods=["GET"])
def get_products():
    """Get all products."""
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows]), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch products: {str(e)}"}), 500

@app.route("/products", methods=["POST"])
@require_token
def add_product():
    """Add a new product (requires API token)."""
    try:
        data = request.get_json()
        
        # Validate request data
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        name = data.get("name")
        price = data.get("price")
        
        # Validate required fields
        if not name:
            return jsonify({"error": "Product name is required"}), 400
        
        if price is None:
            return jsonify({"error": "Product price is required"}), 400
        
        try:
            price = float(price)
        except (ValueError, TypeError):
            return jsonify({"error": "Price must be a valid number"}), 400
        
        if price < 0:
            return jsonify({"error": "Price must be a positive number"}), 400
        
        # Insert product
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, price) VALUES (?, ?)",
            (name.strip(), price)
        )
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        
        new_product = {
            "id": new_id,
            "name": name.strip(),
            "price": price
        }
        
        return jsonify({
            "message": "Product added successfully",
            "product": new_product
        }), 201
        
    except Exception as e:
        return jsonify({"error": f"Failed to add product: {str(e)}"}), 500

@app.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        username = data.get("username")
        password = data.get("password")
        
        # Validate required fields
        if not username:
            return jsonify({"error": "Username is required"}), 400
        
        if not password:
            return jsonify({"error": "Password is required"}), 400
        
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters"}), 400
        
        if len(password) < 6:
            return jsonify({"error": "Password must be at least 6 characters"}), 400
        
        # Hash password
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Insert user
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
        )
        conn.commit()
        conn.close()
        
        return jsonify({
            "message": "User registered successfully",
            "username": username
        }), 201
        
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route("/login", methods=["POST"])
def login():
    """Login a user."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            return jsonify({"error": "Username and password are required"}), 400
        
        # Hash the provided password for comparison
        hashed_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        
        # Query user
        conn = get_db_connection()
        user = conn.execute(
            "SELECT id, username FROM users WHERE username = ? AND password = ?",
            (username, hashed_password)
        ).fetchone()
        conn.close()
        
        if user:
            return jsonify({
                "message": f"Welcome {username}!",
                "user": dict(user)
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors."""
    return jsonify({"error": "Method not allowed"}), 405

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # Initialize database on startup
    with app.app_context():
        try:
            init_db()
            print("Database initialized successfully")
        except Exception as e:
            print(f"Failed to initialize database: {e}")
    
    # Run the application
    app.run(debug=True, host="0.0.0.0", port=5000)