from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from apps.api.product.schemas import UserView


class AdminLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class AdminLoginResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    token_type: str = Field(default="Bearer", alias="tokenType")
    expires_at: datetime = Field(alias="expiresAt")
    user: UserView
