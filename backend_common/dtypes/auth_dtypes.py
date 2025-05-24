from typing import Dict, List, TypeVar, Generic, Optional, Any
from pydantic import BaseModel
from all_types.internal_types import UserId


class ReqAuth(BaseModel):
    email: str
    password: str


class UserProfileSettings(UserId):
    account_type: str = "admin"  # default to admin
    admin_id: Optional[str] = None  # Only required for member accounts
    show_price_on_purchase: bool = False


# Derived classes
class ReqCreateFirebaseUser(ReqAuth):
    username: str


class ReqCreateUserProfile(ReqCreateFirebaseUser, UserProfileSettings):
    user_id: Optional[str] = ""


class ReqUserLogin(ReqAuth):
    pass


class ReqUserProfile(UserId):
    pass


class ReqResetPassword(BaseModel):
    email: str


class ReqConfirmReset(BaseModel):
    oob_code: str
    new_password: str


class ReqChangePassword(UserId, ReqAuth):
    new_password: str


class ReqChangeEmail(UserId):
    current_email: str
    new_email: str
    password: str


class ReqRefreshToken(BaseModel):
    grant_type: str
    refresh_token: str
