import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.rate_limiter import rate_limit_recovery
from app.services.recovery_service import (
    verify_account_for_recovery,
    reset_password_with_token,
    AccountMatchFailedError,
    InvalidRecoveryTokenError,
    ExpiredRecoveryTokenError,
    UsedRecoveryTokenError,
    PasswordValidationError,
    RecoveryServiceUnavailableError,
)

logger = logging.getLogger("shiftly.recovery_endpoint")

router = APIRouter()


class VerifyRecoveryRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="Username or Display Name")
    email: str = Field(..., min_length=3, max_length=255, description="Registered account email address")



class VerifyRecoveryResponse(BaseModel):
    recovery_token: str
    message: str


class ResetPasswordRequest(BaseModel):
    recovery_token: str = Field(..., min_length=10, description="Single-use recovery authorization token")
    new_password: str = Field(..., min_length=8, description="New secure password (minimum 8 characters)")
    confirm_password: str = Field(..., min_length=8, description="Confirmation of new password")


class ResetPasswordResponse(BaseModel):
    success: bool
    message: str


@router.post(
    "/password-recovery/verify",
    response_model=VerifyRecoveryResponse,
    summary="Verify Account for MVP Password Recovery",
    description="Matches supplied username (display name) and email address. Issues a single-use recovery token if matched.",
)
async def verify_recovery(
    payload: VerifyRecoveryRequest,
    _rate_limit: bool = Depends(rate_limit_recovery),
):
    try:
        token = await verify_account_for_recovery(
            username=payload.username,
            email=payload.email,
        )
        return VerifyRecoveryResponse(
            recovery_token=token,
            message="Account verified. Please set your new password.",
        )
    except AccountMatchFailedError as exc:
        # Uniform error message prevents username/email enumeration
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RecoveryServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error during recovery account verification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while verifying account information.",
        )


@router.post(
    "/password-recovery/reset",
    response_model=ResetPasswordResponse,
    summary="Reset Password with Recovery Token",
    description="Updates user password in Supabase Auth using a validated single-use recovery token.",
)
async def reset_password(
    payload: ResetPasswordRequest,
    _rate_limit: bool = Depends(rate_limit_recovery),
):
    try:
        await reset_password_with_token(
            token=payload.recovery_token,
            new_password=payload.new_password,
            confirm_password=payload.confirm_password,
        )
        return ResetPasswordResponse(
            success=True,
            message="Password updated successfully. You can now log in with your new password.",
        )
    except (InvalidRecoveryTokenError, ExpiredRecoveryTokenError, UsedRecoveryTokenError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except PasswordValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except RecoveryServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        logger.exception("Unexpected error during password reset")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the password.",
        )
