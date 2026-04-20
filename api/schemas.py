from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    email: Optional[str] = None

# --- User Schemas ---
class UserBase(BaseModel):
    email: str
    fname: str
    lname: str
    role: str
    group_id: Optional[int] = None
    active: bool = True
    color: str = "#3b82f6"

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    class Config:
        from_attributes = True

# --- Faculty Schemas ---
class FacultyBase(BaseModel):
    name: str
    code: str

class FacultyCreate(FacultyBase):
    pass

class FacultyResponse(FacultyBase):
    id: int
    class Config:
        from_attributes = True

# --- Department Schemas ---
class DepartmentBase(BaseModel):
    name: str
    faculty_id: int

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentResponse(DepartmentBase):
    id: int
    class Config:
        from_attributes = True

# --- Group Schemas ---
class GroupBase(BaseModel):
    name: str
    course: int = 1
    dept_id: int

class GroupCreate(GroupBase):
    pass

class GroupResponse(GroupBase):
    id: int
    class Config:
        from_attributes = True
