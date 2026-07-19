"""Authentication Controller: JWT mock signing and role-based access validation checks."""

from __future__ import annotations

from fastapi import Header, HTTPException, status


class AuthController:
    """Validates user roles and permissions using simulated JWT / API token keys."""

    ROLES = {
        "admin": ["read", "write", "approve", "delete", "marketplace"],
        "creator": ["read", "write", "approve"],
        "reviewer": ["read", "approve"],
        "viewer": ["read"]
    }

    @classmethod
    def verify_token(cls, authorization: str = Header(...)) -> dict:
        """Parse authorization header token and resolve role permissions."""
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format. Prefix header with 'Bearer '."
            )
            
        token = authorization.replace("Bearer ", "").strip()
        
        # Simulated role mappings
        if token == "admin_secret_token":
            return {"user": "admin_user", "role": "admin", "permissions": cls.ROLES["admin"]}
        elif token == "creator_secret_token":
            return {"user": "creator_user", "role": "creator", "permissions": cls.ROLES["creator"]}
        elif token == "reviewer_secret_token":
            return {"user": "reviewer_user", "role": "reviewer", "permissions": cls.ROLES["reviewer"]}
        else:
            # Default viewer role
            return {"user": "guest_user", "role": "viewer", "permissions": cls.ROLES["viewer"]}

    @classmethod
    def check_permission(cls, user_token_info: dict, required_permission: str) -> None:
        """Block request if the token scope does not possess the needed permission."""
        permissions = user_token_info.get("permissions", [])
        if required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access Denied: Scope requires '{required_permission}' permission."
            )
