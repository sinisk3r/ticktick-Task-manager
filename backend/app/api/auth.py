"""
Authentication API endpoints for OAuth flows (TickTick, etc.).

This module handles:
1. OAuth authorization redirect
2. OAuth callback and token exchange
3. Token storage in database
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.ticktick import ticktick_service


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/ticktick/debug")
async def debug_ticktick_config():
    """
    Debug endpoint to check TickTick OAuth configuration.
    """
    auth_url = ticktick_service.get_authorization_url(state="ticktick_oauth")
    return {
        "client_id": ticktick_service.client_id,
        "redirect_uri": ticktick_service.redirect_uri,
        "scope": ticktick_service.SCOPE,
        "authorization_url": auth_url,
    }


@router.get("/ticktick/authorize")
async def authorize_ticktick():
    """
    Redirect user to TickTick OAuth authorization page.

    This endpoint generates the TickTick OAuth URL and redirects the user
    to complete the authorization flow on TickTick's website.

    Returns:
        RedirectResponse to TickTick OAuth page
    """
    # Generate authorization URL with optional state for CSRF protection
    auth_url = ticktick_service.get_authorization_url(state="ticktick_oauth")

    # Redirect user to TickTick for authorization
    return RedirectResponse(url=auth_url)


@router.get("/ticktick/callback")
async def callback_ticktick(
    code: str = Query(..., description="Authorization code from TickTick"),
    state: str = Query(None, description="State parameter for CSRF protection"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle OAuth callback from TickTick.

    This endpoint:
    1. Receives authorization code from TickTick
    2. Exchanges code for access/refresh tokens
    3. Stores tokens in database
    4. Redirects user back to frontend with success/error message

    Args:
        code: Authorization code from TickTick OAuth flow
        state: Optional state parameter for CSRF validation
        db: Database session dependency

    Returns:
        RedirectResponse to frontend with status message

    Raises:
        HTTPException: If token exchange fails
    """
    try:
        # Exchange authorization code for tokens
        print(f"[DEBUG] Exchanging code: {code[:10]}... for tokens")
        token_data = await ticktick_service.exchange_code_for_token(code, db)
        print(f"[DEBUG] Token exchange successful, got access_token")

        # For now, use a default user_id=1 (single-user mode)
        # In multi-user mode, this would come from session/JWT
        user_id = 1

        # Store tokens in database
        print(f"[DEBUG] Storing tokens for user_id={user_id}")
        user = await ticktick_service.store_tokens(db, user_id, token_data)
        print(f"[DEBUG] Tokens stored successfully")

        # Get user info from TickTick to store user_id
        try:
            user_info = await ticktick_service.get_user_info(
                token_data["access_token"]
            )
            user.ticktick_user_id = str(user_info.get("userId", ""))
            await db.commit()
            print(f"[DEBUG] User info fetched, ticktick_user_id={user.ticktick_user_id}")
        except Exception as e:
            # Non-critical - continue even if user info fetch fails
            print(f"[WARN] Could not fetch TickTick user info: {e}")

        # Redirect to frontend with success message
        from app.core.config import settings
        frontend_url = settings.frontend_url
        redirect_url = f"{frontend_url}/auth/callback?status=success&message=TickTick+connected+successfully"
        print(f"[DEBUG] Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        # Handle errors and redirect to frontend with error message
        import traceback
        error_details = traceback.format_exc()
        print(f"[ERROR] TickTick OAuth callback failed:\n{error_details}")

        from app.core.config import settings
        frontend_url = settings.frontend_url
        error_msg = str(e).replace(" ", "+")[:100]  # Truncate long errors
        return RedirectResponse(
            url=f"{frontend_url}/auth/callback?status=error&message={error_msg}"
        )


@router.post("/ticktick/disconnect")
async def disconnect_ticktick(db: AsyncSession = Depends(get_db)):
    """
    Disconnect TickTick integration by clearing stored tokens.

    This endpoint removes TickTick OAuth tokens from the database,
    effectively disconnecting the user's TickTick account.

    Args:
        db: Database session dependency

    Returns:
        Success message

    Raises:
        HTTPException: If user not found
    """
    from app.models.user import User
    from sqlalchemy import select

    # For now, use default user_id=1 (single-user mode)
    user_id = 1

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Clear TickTick tokens
    user.ticktick_access_token = None
    user.ticktick_refresh_token = None
    user.ticktick_user_id = None

    await db.commit()

    return {"message": "TickTick disconnected successfully"}


@router.get("/ticktick/status")
async def get_ticktick_status(db: AsyncSession = Depends(get_db)):
    """
    Check if TickTick is connected for the current user.

    Returns connection status and basic user information if connected.

    Args:
        db: Database session dependency

    Returns:
        Dictionary with connection status:
        {
            "connected": bool,
            "ticktick_user_id": str | None
        }
    """
    from app.models.user import User
    from sqlalchemy import select

    # For now, use default user_id=1 (single-user mode)
    user_id = 1

    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.ticktick_access_token:
        return {
            "connected": False,
            "ticktick_user_id": None
        }

    return {
        "connected": True,
        "ticktick_user_id": user.ticktick_user_id
    }
