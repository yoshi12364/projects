from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import List, Optional
import uuid
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware

# ---------------- APP --------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- PASSWORD ----------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str):
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False

# ---------------- DATABASE ----------------
DATABASE_URL = "postgresql://postgres:yoshitha.2@localhost:5432/userdb"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ---------------- MODELS ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    mobileNumber = Column(String, unique=True, nullable=False)

class UserSession(Base):
    __tablename__ = "user_sessions"

    userid = Column(Integer, ForeignKey("users.id"), primary_key=True)
    sessionid = Column(String, unique=True, nullable=False)

# ---------------- SCHEMAS ----------------
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    mobileNumber: str

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    mobileNumber: str

class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    session_id: str

# ---------------- CREATE TABLES ----------------
Base.metadata.create_all(bind=engine)

# ---------------- DB DEPENDENCY ----------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
class AuthenticationRequest(BaseModel):
    userid: int
    sessionid: str

class AuthenticateResponse(BaseModel):
    success: str
@app.post("/authenticate", response_model=AuthenticateResponse)
def authenticate_external(request: AuthenticationRequest, db: Session = Depends(get_db)):
    user_session = (
        db.query(UserSession)
        .filter(
            UserSession.userid == request.userid,
            UserSession.sessionid == request.sessionid
        )
        .first()
    )

    if not user_session:
        raise HTTPException(
            status_code=403,
            detail="Invalid or expired session. Please login again"
        )

    return {"success": "true"}

# ---------------- SESSION VALIDATION ----------------
def validate_session(
    session_id: Optional[str] = Header(None, alias="Session-Id"),
    db: Session = Depends(get_db)
):
    if not session_id:
        raise HTTPException(status_code=401, detail="Session ID missing")

    session = db.query(UserSession).filter(
        UserSession.sessionid == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    return session.userid

# ---------------- LOGIN ----------------
@app.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    

    session_id = str(uuid.uuid4())

    existing = db.query(UserSession).filter(
        UserSession.userid == user.id
    ).first()

    if existing:
        existing.sessionid = session_id
    else:
        db.add(UserSession(userid=user.id, sessionid=session_id))

    db.commit()

    return {"session_id": session_id}

# ---------------- CREATE USER ----------------
@app.post("/users", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
    
):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = User(
        name=user.name,
        email=user.email,
        password=(user.password),
        mobileNumber=user.mobileNumber
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# ---------------- READ USERS ----------------
@app.get("/users", response_model=List[UserResponse])
def get_users(
    user_id: int = Depends(validate_session),
    db: Session = Depends(get_db)
):
    return db.query(User).all()

# ---------------- UPDATE USER ----------------
@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserCreate,
    current_user: int = Depends(validate_session),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.id == user_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    existing.name = user.name
    existing.email = user.email
    existing.password = hash_password(user.password)
    existing.mobileNumber = user.mobileNumber

    db.commit()
    db.refresh(existing)
    return existing

# ---------------- DELETE USER ----------------
@app.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: int = Depends(validate_session),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}