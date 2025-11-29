import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from datetime import datetime, timedelta
import yaml

with open("config/settings.yaml", "r") as f:
    config = yaml.safe_load(f)

SECRET_KEY = config['supervisor']['jwt_secret']
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

# Pre-hashed password for "password"
# Generated with: bcrypt.hashpw(b'password', bcrypt.gensalt())
PREHASHED_PASSWORD = b'$2b$12$gLN3LTjAa2D98ncp8qiZkeBhuTNNiz8BsC6MWwV6eylH6OUc9S8ii'

# In-memory user store for simplicity
users_db = {
    "test@example.com": {
        "id": "1",
        "name": "Test User",
        "email": "test@example.com",
        "avatar": None,
        "password_hash": PREHASHED_PASSWORD
    }
}

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def login(payload: dict):
    email = payload.get("email")
    password = payload.get("password") # Assuming password is provided for a real login
    user_data = users_db.get(email)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    # Verify password using bcrypt
    if not bcrypt.checkpw(password.encode('utf-8'), user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    from shared.models import User
    user = User(**{k: v for k, v in user_data.items() if k != 'password_hash'})
    
    access_token = create_access_token(data={"sub": user.email})
    return {"user": user, "token": access_token}

def require_auth(auth: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user_data = users_db.get(email)
        if user_data is None:
            raise HTTPException(status_code=401, detail="User not found")

        from shared.models import User
        user = User(**{k: v for k, v in user_data.items() if k != 'password_hash'})
        return user

    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
