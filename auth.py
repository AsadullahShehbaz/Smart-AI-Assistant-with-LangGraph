"""
User Authentication System
"""
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
import config


class AuthSystem:
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.setup_database()
    
    def setup_database(self):
        """Create users table if it doesn't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                subscription_tier TEXT DEFAULT 'free'
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        conn.commit()
        conn.close()
        print("✅ Auth database initialized")
    
    def hash_password(self, password: str) -> str:
        """Hash password with SHA256"""
        salt = config.PASSWORD_SALT if hasattr(config, 'PASSWORD_SALT') else "default_salt"
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def register_user(self, username: str, email: str, password: str) -> dict:
        """Register new user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Validate input
            if len(username) < 3:
                return {"success": False, "error": "Username must be at least 3 characters"}
            
            if len(password) < 6:
                return {"success": False, "error": "Password must be at least 6 characters"}
            
            if "@" not in email:
                return {"success": False, "error": "Invalid email format"}
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            """, (username, email, password_hash))
            
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            
            return {
                "success": True,
                "user_id": user_id,
                "message": "Account created successfully!"
            }
            
        except sqlite3.IntegrityError as e:
            if "username" in str(e):
                return {"success": False, "error": "Username already exists"}
            elif "email" in str(e):
                return {"success": False, "error": "Email already registered"}
            else:
                return {"success": False, "error": "Registration failed"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def login_user(self, username: str, password: str) -> dict:
        """Login user and create session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Check credentials
            cursor.execute("""
                SELECT user_id, username, email, subscription_tier
                FROM users
                WHERE username = ? AND password_hash = ? AND is_active = 1
            """, (username, password_hash))
            
            user = cursor.fetchone()
            
            if not user:
                conn.close()
                return {"success": False, "error": "Invalid username or password"}
            
            user_id, username, email, tier = user
            
            # Create session
            session_id = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(days=7)
            
            cursor.execute("""
                INSERT INTO sessions (session_id, user_id, expires_at)
                VALUES (?, ?, ?)
            """, (session_id, user_id, expires_at))
            
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "session_id": session_id,
                "user_id": user_id,
                "username": username,
                "email": email,
                "subscription_tier": tier,
                "message": "Login successful!"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def verify_session(self, session_id: str) -> dict:
        """Check if session is valid"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT s.user_id, u.username, u.email, u.subscription_tier
                FROM sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.session_id = ? AND s.expires_at > CURRENT_TIMESTAMP
            """, (session_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                user_id, username, email, tier = result
                return {
                    "valid": True,
                    "user_id": user_id,
                    "username": username,
                    "email": email,
                    "subscription_tier": tier
                }
            else:
                return {"valid": False}
                
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def logout_user(self, session_id: str):
        """Delete session"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            conn.close()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_user_stats(self, user_id: int) -> dict:
        """Get user statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT username, email, created_at, last_login, subscription_tier
                FROM users WHERE user_id = ?
            """, (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    "username": result[0],
                    "email": result[1],
                    "member_since": result[2],
                    "last_login": result[3],
                    "subscription_tier": result[4]
                }
            return {}
            
        except Exception as e:
            return {"error": str(e)}


# Initialize auth system
auth = AuthSystem()