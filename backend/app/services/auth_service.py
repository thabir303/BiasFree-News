"""
Authentication service for user management and JWT token handling.
"""
from datetime import datetime, timedelta
from typing import Optional
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database.models import User, UserRole
from app.models.schemas import UserSignup, UserResponse
from app.config import settings


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token security
security = HTTPBearer()


class AuthService:
    """Service for handling authentication operations."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: Data to encode in the token
            expires_delta: Optional expiration time delta
            
        Returns:
            Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            # Default to 7 days
            expire = datetime.utcnow() + timedelta(days=7)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow()
        })
        
        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> dict:
        """
        Decode and verify a JWT token.
        
        Args:
            token: JWT token to decode
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm]
            )
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def create_user(db: Session, user_data: UserSignup, role: UserRole = UserRole.USER) -> User:
        """
        Create a new user.
        
        Args:
            db: Database session
            user_data: User signup data
            role: User role (default: USER)
            
        Returns:
            Created user
            
        Raises:
            HTTPException: If email already exists
        """
        # Check if email exists (username doesn't need to be unique)
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create new user
        hashed_password = AuthService.hash_password(user_data.password)
        verification_token = AuthService.generate_verification_token()
        
        # Set token expiration
        token_expires_at = datetime.utcnow() + timedelta(
            minutes=settings.verification_token_expiration_minutes
        )
        
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role=role,
            verification_token=verification_token,
            token_expires_at=token_expires_at,
            is_verified=False
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        return db_user
    
    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            db: Database session
            email: User email
            password: Plain password
            
        Returns:
            User if authentication successful, None otherwise
        """
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            return None
        
        if not AuthService.verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            return None
        
        if not user.is_verified:
            return "not_verified"  # Special return value for unverified users
        
        return user
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email."""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def create_admin_user(db: Session) -> Optional[User]:
        """
        Create admin user from environment variables if not exists.
        
        Args:
            db: Database session
            
        Returns:
            Admin user or None if already exists
        """
        # Check if admin already exists
        admin_user = db.query(User).filter(User.email == settings.admin_email).first()
        
        if admin_user:
            return None
        
        # Create admin user
        hashed_password = AuthService.hash_password(settings.admin_password)
        admin = User(
            username=settings.admin_username,
            email=settings.admin_email,
            hashed_password=hashed_password,
            role=UserRole.ADMIN,
            is_verified=True  # Admin is auto-verified
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        return admin
    
    @staticmethod
    def generate_verification_token() -> str:
        """Generate a random verification token."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def verify_email(db: Session, token: str) -> bool:
        """
        Verify user email with token.
        
        Args:
            db: Database session
            token: Verification token
            
        Returns:
            True if verification successful, False otherwise
        """
        user = db.query(User).filter(User.verification_token == token).first()
        
        if not user:
            return False
        
        # Check if token has expired
        if user.token_expires_at and user.token_expires_at < datetime.utcnow():
            return False
        
        user.is_verified = True
        user.verification_token = None
        user.token_expires_at = None
        db.commit()
        
        return True


# Dependency for getting current user from JWT token
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(lambda: None)  # Will be properly injected
) -> User:
    """
    Dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
        
    Returns:
        Current authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    from app.database.database import get_db
    
    # Get database session if not provided
    if db is None:
        db = next(get_db())
    
    token = credentials.credentials
    
    # Decode token
    payload = AuthService.decode_token(token)
    user_id: str = payload.get("sub")
    
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = AuthService.get_user_by_id(db, int(user_id))
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


# Dependency to require admin role
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require admin role.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user if admin
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    return current_user


# Dependency to require authenticated user (any role)
async def require_authenticated(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to require any authenticated user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current authenticated user
    """
    return current_user
