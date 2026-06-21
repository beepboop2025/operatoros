"""Authentication routes — login, registration, profile management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.middleware.audit import get_client_ip, log_action
from app.middleware.auth import create_access_token, create_refresh_token, hash_password, verify_password, verify_token
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserResponseNested
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(tags=["auth"])


# --------------------------------------------------------------------------- #
#  POST /login
# --------------------------------------------------------------------------- #


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT",
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user with email and password, returning a JWT access token."""

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token({"sub": user.id, "role": user.role.value})
    refresh = create_refresh_token({"sub": user.id, "role": user.role.value})

    await log_action(
        db,
        user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        ip_address=get_client_ip(request),
    )

    return TokenResponse(
        access_token=token,
        refresh_token=refresh,
        user=UserResponseNested(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        ),
    )


# --------------------------------------------------------------------------- #
#  POST /refresh
# --------------------------------------------------------------------------- #


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_access_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Issue a new access token from a valid refresh token.

    The refresh token is verified using the same JWT secret and algorithm as
    access tokens. A new token is returned along with the user's profile.
    """
    payload = verify_token(body.refresh_token, expected_type="refresh")

    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive account",
        )

    new_token = create_access_token({"sub": user.id, "role": user.role.value})
    # Rotate the refresh token on every use.
    new_refresh = create_refresh_token({"sub": user.id, "role": user.role.value})

    return TokenResponse(
        access_token=new_token,
        refresh_token=new_refresh,
        user=UserResponseNested(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=user.role.value,
            is_active=user.is_active,
        ),
    )


# --------------------------------------------------------------------------- #
#  POST /register  (admin only)
# --------------------------------------------------------------------------- #


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (admin only)",
)
async def register(
    body: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
) -> UserResponse:
    """Create a new user account. Only administrators can register users."""

    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole(body.role.value),
    )
    db.add(user)
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="user.register",
        entity_type="user",
        entity_id=user.id,
        details={"email": body.email, "role": body.role.value},
        ip_address=get_client_ip(request),
    )

    return UserResponse.model_validate(user)


# --------------------------------------------------------------------------- #
#  GET /me
# --------------------------------------------------------------------------- #


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


# --------------------------------------------------------------------------- #
#  PUT /me
# --------------------------------------------------------------------------- #


@router.put(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_me(
    body: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Update the authenticated user's profile (full_name only; role changes require admin)."""

    if body.full_name is not None:
        current_user.full_name = body.full_name

    # Non-admin users cannot change their own role or active status
    if body.role is not None and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change user roles",
        )
    if body.role is not None:
        current_user.role = UserRole(body.role.value)

    if body.is_active is not None and current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change active status",
        )
    if body.is_active is not None:
        if body.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate your own account",
            )
        current_user.is_active = body.is_active

    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="user.update_profile",
        entity_type="user",
        entity_id=current_user.id,
        ip_address=get_client_ip(request),
    )

    return UserResponse.model_validate(current_user)


# --------------------------------------------------------------------------- #
#  POST /change-password
# --------------------------------------------------------------------------- #


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change current user's password",
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Change the authenticated user's password. Requires current password for verification."""

    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = hash_password(body.new_password)
    await db.flush()

    await log_action(
        db,
        user_id=current_user.id,
        action="user.change_password",
        entity_type="user",
        entity_id=current_user.id,
        ip_address=get_client_ip(request),
    )

    return {"detail": "Password updated successfully"}
