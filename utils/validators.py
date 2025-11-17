"""
Request validation schemas using Pydantic
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Literal
from decimal import Decimal

class UserRegistrationSchema(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8)
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class AccountCreationSchema(BaseModel):
    account_type: Literal['checking', 'savings']
    opening_balance: Decimal = Field(default=0, ge=0)
    user_id: Optional[int] = None

class TransferSchema(BaseModel):
    from_account_id: int = Field(..., gt=0)
    to_account_id: Optional[int] = Field(None, gt=0)
    to_account_number: Optional[str] = None
    amount: Decimal = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=500)
    idempotency_key: Optional[str] = Field(None, max_length=100)
    
    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 1000000:
            raise ValueError('Amount exceeds maximum transfer limit')
        return v

class AccountStatusUpdateSchema(BaseModel):
    status: Literal['active', 'frozen', 'closed']
    reason: Optional[str] = Field(None, max_length=500)

class UserUpdateSchema(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=10, max_length=20)
    role: Optional[Literal['customer', 'support_agent', 'auditor', 'admin']] = None

class PasswordChangeSchema(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v

class SupportTicketSchema(BaseModel):
    subject: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=10)
    
class TicketNoteSchema(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)
