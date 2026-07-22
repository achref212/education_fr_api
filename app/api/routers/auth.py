from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_auth_service,
    get_current_account,
    get_current_user,
    get_school_repo,
    get_user_repo,
)
from app.api.schemas.school import SchoolOut, SchoolPublicOut, SchoolTokenResponse
from app.api.schemas.user import (
    ChangePasswordIn,
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    MessageResponse,
    ProfileUpdateIn,
    RegisterIn,
    RegisterOut,
    ResendActivationIn,
    ResendActivationOut,
    ResetPasswordIn,
    ResetTokenResponse,
    TokenResponse,
    UserOut,
    VerifyRegistrationIn,
    VerifyResetCodeIn,
)
from app.application.auth_service import AuthError, AuthService
from app.domain.entities import School, User
from app.domain.ports import ISchoolRepository, IUserRepository
from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/schools", response_model=list[SchoolPublicOut])
def list_public_schools(
    schools: ISchoolRepository = Depends(get_school_repo),
) -> list[SchoolPublicOut]:
    """Active schools available for student self-registration."""
    return [
        SchoolPublicOut.from_domain(s)
        for s in schools.list_all()
        if s.is_active
    ]


@router.post("/register", response_model=RegisterOut, status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> RegisterOut:
    try:
        user, state_token = auth.register(
            email=body.email,
            password=body.password,
            first_name=body.firstName,
            last_name=body.lastName,
            level=body.level,
            phone=body.phone,
            date_of_birth=body.dateOfBirth,
            class_level=body.classLevel,
            school_id=str(body.schoolId) if body.schoolId else None,
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
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet e-mail est déjà utilisé",
        ) from exc
    return RegisterOut(
        message="Un code d'activation a été envoyé à votre adresse e-mail.",
        registration_state_token=state_token,
    )


@router.post("/verify-registration", response_model=TokenResponse)
def verify_registration(
    body: VerifyRegistrationIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    try:
        user, token = auth.verify_registration(
            body.email, body.code, body.registration_state_token
        )
        db.commit()
    except AuthError as e:
        db.rollback()
        if e.code == "already_active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
            ) from e
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user=UserOut.from_domain(user),
    )


@router.post("/resend-activation", response_model=ResendActivationOut)
def resend_activation(
    body: ResendActivationIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> ResendActivationOut:
    state_token = auth.resend_activation_code(body.email)
    db.commit()
    return ResendActivationOut(
        message="Si le compte existe et n'est pas activé, un nouveau code a été envoyé.",
        registration_state_token=state_token,
    )


def _raise_auth_http_error(exc: AuthError) -> None:
    if exc.code == "account_inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=exc.message
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
    ) from exc


@router.post("/login")
def login(
    body: LoginIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> TokenResponse | SchoolTokenResponse:
    """
    Unified login endpoint.
    - Returns TokenResponse for users (student / prof / admin)
    - Returns SchoolTokenResponse for school accounts

    Password is matched against user and school records so professor and
    school accounts can coexist on the same email when needed.
    """
    try:
        account_type, account, token = auth.authenticate_portal(
            body.email, body.password
        )
        db.commit()
    except AuthError as e:
        db.rollback()
        _raise_auth_http_error(e)

    if account_type == "school":
        school = account
        assert isinstance(school, School)
        return SchoolTokenResponse(
            access_token=token,
            token_type="bearer",
            role="school",
            school=SchoolOut.from_domain(school),
        )

    user = account
    assert isinstance(user, User)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user=UserOut.from_domain(user),
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_domain(user)


@router.patch("/me", response_model=UserOut)
def update_me(
    body: ProfileUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
) -> UserOut:
    if user.role not in ("admin", "prof", "user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profil non modifiable pour ce type de compte",
        )
    try:
        updated = auth.update_user_profile(
            user,
            first_name=body.firstName,
            last_name=body.lastName,
            phone=body.phone,
            date_of_birth=body.dateOfBirth,
            profile_picture_url=body.profilePictureUrl,
            clear_profile_picture_url=(
                "profilePictureUrl" in body.model_fields_set
                and body.profilePictureUrl is None
            ),
        )
        db.commit()
    except AuthError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    return UserOut.from_domain(updated)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordIn,
    db: Session = Depends(get_db),
    account: User | School = Depends(get_current_account),
    auth: AuthService = Depends(get_auth_service),
) -> None:
    try:
        auth.change_password(account, body.oldPassword, body.newPassword)
        db.commit()
    except AuthError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e


@router.post("/forgot-password", response_model=ForgotPasswordOut)
def forgot_password(
    body: ForgotPasswordIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> ForgotPasswordOut:
    state_token = auth.request_portal_password_reset(body.email)
    db.commit()
    return ForgotPasswordOut(
        message=(
            "Si un compte est associé à cet e-mail, "
            "vous recevrez un code de réinitialisation."
        ),
        reset_state_token=state_token,
    )


@router.post("/verify-reset-code", response_model=ResetTokenResponse)
def verify_reset_code(
    body: VerifyResetCodeIn,
    db: Session = Depends(get_db),
    auth: AuthService = Depends(get_auth_service),
) -> ResetTokenResponse:
    try:
        reset_token = auth.verify_portal_reset_code(
            body.email, body.code, body.reset_state_token
        )
        db.commit()
    except AuthError as e:
        db.rollback()
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
        auth.reset_portal_password(body.email, body.reset_token, body.new_password)
        db.commit()
    except AuthError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    return MessageResponse(message="Mot de passe réinitialisé avec succès.")
