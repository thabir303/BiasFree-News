"""
Authentication API routes for user signup, signin, and profile.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.schemas import UserSignup, UserSignin, TokenResponse, UserResponse, CategoryPreferencesRequest, CategoryPreferencesResponse, UserAnalysisCreate, UserAnalysisResponse, UserAnalysesListResponse, ForgotPasswordRequest, VerifyOtpRequest, ResetPasswordRequest
from app.services.auth_service import AuthService, get_current_user
from app.services.email_service import email_service
from app.database.models import User, UserAnalysis
from app.config import settings
import logging
import random

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: UserSignup,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    - **username**: Unique username (3-50 characters)
    - **email**: Valid email address
    - **password**: Password (minimum 6 characters)
    
    Returns JWT access token and user information.
    Note: Email verification required before signin.
    """
    try:
        # Create new user
        user = AuthService.create_user(db, user_data)
        
        # Send verification email
        email_sent = email_service.send_verification_email(
            to_email=user.email,
            username=user.username,
            verification_token=user.verification_token
        )
        
        if not email_sent:
            logger.warning(f"Failed to send verification email to {user.email}, but user created successfully")
        
        # Create access token (but signin will require verification)
        access_token = AuthService.create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )
        
        # Prepare response
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            category_preferences=user.category_preferences
        )
        
        message = "Account created successfully! A verification email has been sent to your email address. Please check your inbox and verify your email to login."
        if not email_sent:
            message = "Account created successfully! However, we couldn't send the verification email. Please contact support or try resending the verification email."
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response,
            message=message
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )


@router.post("/signin", response_model=TokenResponse)
async def signin(
    credentials: UserSignin,
    db: Session = Depends(get_db)
):
    """
    Sign in with email and password.
    
    - **email**: User email address
    - **password**: User password
    
    Returns JWT access token and user information.
    """
    # Authenticate user
    user = AuthService.authenticate_user(db, credentials.email, credentials.password)
    
    # Check if email not verified
    if user == "not_verified":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please verify your email before signing in.",
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = AuthService.create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )
    
    # Prepare response
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        category_preferences=user.category_preferences
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    
    Requires valid JWT token in Authorization header.
    """
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.value,
        is_active=current_user.is_active,
        category_preferences=current_user.category_preferences
    )


@router.get("/verify")
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """
    Verify JWT token validity.
    
    Returns simple success response if token is valid.
    """
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "role": current_user.role.value
    }


@router.post("/verify-email/{token}")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verify user email with verification token.
    
    - **token**: Email verification token received after signup
    
    Returns success message if verification successful.
    """
    success = AuthService.verify_email(db, token)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    return {
        "message": "Email verified successfully! You can now sign in."
    }


@router.post("/resend-verification/{email}")
async def resend_verification(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Resend verification email to user.
    
    - **email**: User email address
    
    Returns new verification token.
    """
    user = AuthService.get_user_by_email(db, email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified"
        )
    
    # Generate new token with new expiration time
    new_token = AuthService.generate_verification_token()
    token_expires_at = datetime.utcnow() + timedelta(
        minutes=settings.verification_token_expiration_minutes
    )
    
    user.verification_token = new_token
    user.token_expires_at = token_expires_at
    db.commit()
    
    # Send verification email
    email_sent = email_service.send_verification_email(
        to_email=user.email,
        username=user.username,
        verification_token=new_token
    )
    
    if not email_sent:
        logger.warning(f"Failed to send verification email to {user.email}")
        return {
            "message": "Failed to send verification email. Please try again later.",
            "success": False
        }
    
    return {
        "message": "Verification email sent successfully! Please check your inbox.",
        "success": True
    }


# ============================================
# Forgot Password / Reset Password (OTP)
# ============================================

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Send a 6-digit OTP to the user's email for password reset.
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        # Don't reveal whether email exists — always return success-like message
        return {
            "message": "If an account exists with that email, an OTP has been sent.",
            "success": True
        }
    
    # Generate 6-digit OTP
    otp = f"{random.randint(100000, 999999)}"
    
    # Store OTP with 10-minute expiry
    user.reset_otp = otp
    user.reset_otp_expires_at = datetime.utcnow() + timedelta(minutes=10)
    db.commit()
    
    # Send OTP email
    email_sent = email_service.send_password_reset_otp(
        to_email=user.email,
        username=user.username,
        otp=otp
    )
    
    if not email_sent:
        logger.warning(f"Failed to send reset OTP to {user.email}")
        return {
            "message": "Failed to send OTP email. Please try again.",
            "success": False
        }
    
    return {
        "message": "If an account exists with that email, an OTP has been sent.",
        "success": True
    }


@router.post("/verify-otp")
async def verify_otp(
    request: VerifyOtpRequest,
    db: Session = Depends(get_db)
):
    """
    Verify the OTP sent to user's email.
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or OTP"
        )
    
    if not user.reset_otp or user.reset_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    if user.reset_otp_expires_at and user.reset_otp_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )
    
    return {
        "message": "OTP verified successfully. You can now reset your password.",
        "valid": True
    }


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using verified OTP.
    """
    user = db.query(User).filter(User.email == request.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or OTP"
        )
    
    if not user.reset_otp or user.reset_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    if user.reset_otp_expires_at and user.reset_otp_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired. Please request a new one."
        )
    
    # Update password
    user.hashed_password = AuthService.hash_password(request.new_password)
    
    # Mark email as verified (user proved ownership via OTP)
    user.is_verified = True
    
    # Clear OTP
    user.reset_otp = None
    user.reset_otp_expires_at = None
    db.commit()
    
    return {
        "message": "Password reset successfully! You can now sign in with your new password.",
        "success": True
    }


@router.get("/preferences", response_model=CategoryPreferencesResponse)
async def get_category_preferences(
    current_user: User = Depends(get_current_user)
):
    """
    Get user's category preferences (priority order).
    
    Returns ordered list of category keys.
    """
    prefs = current_user.category_preferences or []
    return CategoryPreferencesResponse(categories=prefs)


@router.put("/preferences", response_model=CategoryPreferencesResponse)
async def update_category_preferences(
    request: CategoryPreferencesRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user's category preferences (priority order).
    
    - **categories**: Ordered list of category keys, e.g. ["রাজনীতি", "বিশ্ব", "মতামত", "বাংলাদেশ"]
    
    The first category has highest priority.
    """
    VALID_CATEGORIES = {"রাজনীতি", "বিশ্ব", "মতামত", "বাংলাদেশ"}
    
    # Validate that all categories are valid
    for cat in request.categories:
        if cat not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid category: {cat}. Valid categories: {', '.join(VALID_CATEGORIES)}"
            )
    
    # Remove duplicates while preserving order
    seen = set()
    unique_categories = []
    for cat in request.categories:
        if cat not in seen:
            seen.add(cat)
            unique_categories.append(cat)
    
    # Re-fetch user within THIS db session to avoid detached instance error
    user = db.query(User).filter(User.id == current_user.id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.category_preferences = unique_categories
    db.commit()
    
    return CategoryPreferencesResponse(
        categories=unique_categories,
        message="Category preferences updated successfully!"
    )


# ============================================
# User Manual Analysis Endpoints
# ============================================

@router.post("/analyses", response_model=UserAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def save_user_analysis(
    analysis_data: UserAnalysisCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save a manual analysis result for the current user.
    """
    try:
        analysis = UserAnalysis(
            user_id=current_user.id,
            title=analysis_data.title,
            original_content=analysis_data.original_content,
            is_biased=analysis_data.is_biased,
            bias_score=analysis_data.bias_score,
            bias_summary=analysis_data.bias_summary,
            biased_terms=analysis_data.biased_terms,
            confidence=analysis_data.confidence,
            debiased_content=analysis_data.debiased_content,
            changes_made=analysis_data.changes_made,
            total_changes=analysis_data.total_changes,
            generated_headlines=analysis_data.generated_headlines,
            recommended_headline=analysis_data.recommended_headline,
            headline_reasoning=analysis_data.headline_reasoning,
            processing_time=analysis_data.processing_time,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        return UserAnalysisResponse(
            id=analysis.id,
            user_id=analysis.user_id,
            title=analysis.title,
            original_content=analysis.original_content,
            is_biased=analysis.is_biased,
            bias_score=analysis.bias_score,
            bias_summary=analysis.bias_summary,
            biased_terms=analysis.biased_terms,
            confidence=analysis.confidence,
            debiased_content=analysis.debiased_content,
            changes_made=analysis.changes_made,
            total_changes=analysis.total_changes,
            generated_headlines=analysis.generated_headlines,
            recommended_headline=analysis.recommended_headline,
            headline_reasoning=analysis.headline_reasoning,
            processing_time=analysis.processing_time,
            created_at=analysis.created_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"Error saving user analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save analysis: {str(e)}"
        )


@router.get("/analyses", response_model=UserAnalysesListResponse)
async def get_user_analyses(
    limit: int = 20,
    skip: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all manual analyses for the current user, newest first.
    """
    total = db.query(UserAnalysis).filter(UserAnalysis.user_id == current_user.id).count()
    analyses = (
        db.query(UserAnalysis)
        .filter(UserAnalysis.user_id == current_user.id)
        .order_by(UserAnalysis.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    return UserAnalysesListResponse(
        analyses=[
            UserAnalysisResponse(
                id=a.id,
                user_id=a.user_id,
                title=a.title,
                original_content=a.original_content,
                is_biased=a.is_biased,
                bias_score=a.bias_score,
                bias_summary=a.bias_summary,
                biased_terms=a.biased_terms,
                confidence=a.confidence,
                debiased_content=a.debiased_content,
                changes_made=a.changes_made,
                total_changes=a.total_changes,
                generated_headlines=a.generated_headlines,
                recommended_headline=a.recommended_headline,
                headline_reasoning=a.headline_reasoning,
                processing_time=a.processing_time,
                created_at=a.created_at.isoformat(),
            )
            for a in analyses
        ],
        total=total,
    )


@router.delete("/analyses/{analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a manual analysis owned by the current user.
    """
    analysis = (
        db.query(UserAnalysis)
        .filter(UserAnalysis.id == analysis_id, UserAnalysis.user_id == current_user.id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    db.delete(analysis)
    db.commit()
