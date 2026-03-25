from datetime import date
from typing import Optional

from pydantic import BaseModel


class EmployeeBase(BaseModel):
    full_name: str
    employee_code: Optional[str] = None
    date_of_birth: Optional[date] = None
    hometown: Optional[str] = None
    join_date: Optional[date] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    permanent_address: Optional[str] = None
    position: Optional[str] = None
    status_id: Optional[int] = None
    notes: Optional[str] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    employee_code: Optional[str] = None
    date_of_birth: Optional[date] = None
    hometown: Optional[str] = None
    join_date: Optional[date] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    permanent_address: Optional[str] = None
    position: Optional[str] = None
    status_id: Optional[int] = None
    notes: Optional[str] = None


class EmployeeOut(EmployeeBase):
    id: int
    folder_path: Optional[str] = None
    file_path: Optional[str] = None


class EmployeeList(BaseModel):
    total: int
    employees: list[EmployeeOut]
