from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_auth_service, get_current_user, get_user_repo
from app.api.schemas.user import (
    LoginIn,
    RegisterIn,
    TokenResponse,
    UserOut,
)
from app.application.auth_service import AuthError, AuthService
from app.domain.entities import User
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        user, token = auth.register(
            email=body.email,
            password=body.password,
            first_name=body.firstName,
            last_name=body.lastName,
            level=body.level,
        )
        db.commit()
    except AuthError as e:
        db.rollback()
        from fastapi import HTTPException

        if e.code == "email_taken":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message) from e
        raise
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.from_domain(user),
    )


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        user, token = auth.login(body.email, body.password)
        db.commit()
    except AuthError as e:
        db.rollback()
        from fastapi import HTTPException

        if e.code == "account_inactive":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=e.message
            ) from e
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=e.message
        ) from e
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.from_domain(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_domain(user)
