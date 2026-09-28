from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import signup_user, login_user
from app.utils.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    """
    Create a new account.
    Frontend call: POST /api/v1/auth/signup  { name, email, password }
    Returns a JWT immediately (user is signed in right after signup).
    """
    user, token = signup_user(db, payload)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Frontend call: POST /api/v1/auth/login  { email, password }
    """
    user, token = login_user(db, payload)
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Frontend call: GET /api/v1/auth/me   (Authorization: Bearer <token>)
    """
    return UserResponse.model_validate(current_user)
