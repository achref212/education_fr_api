from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_auth_service, get_current_user, get_user_repo
from app.api.schemas.user import (
    ForgotPasswordIn,
    LoginIn,
    MessageResponse,
    RegisterIn,
    ResetPasswordIn,
    ResetTokenResponse,
    TokenResponse,
    UserOut,
    VerifyResetCodeIn,
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
        if e.code == "email_taken":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message) from e
        if e.code == "invalid_email":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=e.message
            ) from e
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


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    body: ForgotPasswordIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    auth.request_password_reset(body.email)
    db.commit()
    return MessageResponse(
        message=(
            "Si un compte est associé à cet e-mail, "
            "vous recevrez un code de réinitialisation."
        )
    )


@router.post("/verify-reset-code", response_model=ResetTokenResponse)
def verify_reset_code(
    body: VerifyResetCodeIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> ResetTokenResponse:
    try:
        reset_token = auth.verify_reset_code(body.email, body.code)
        db.commit()
    except AuthError as e:
        db.rollback()
        if e.code == "too_many_attempts":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=e.message
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    return ResetTokenResponse(reset_token=reset_token)


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    body: ResetPasswordIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    try:
        auth.reset_password(body.reset_token, body.new_password)
        db.commit()
    except AuthError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    return MessageResponse(message="Mot de passe réinitialisé avec succès.")
