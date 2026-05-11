from pydantic import BaseModel, EmailStr, field_validator

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    def username_valid(cls, v):
        if len(v) < 3 or len(v) > 20:
            raise ValueError("Username must be 3-20 characters")
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric only")
        return v

    @field_validator("password")
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    token_type:    str = "bearer"