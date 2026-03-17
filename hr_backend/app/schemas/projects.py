from datetime import date
from typing import Optional

from pydantic import BaseModel


class ProjectBase(BaseModel):
    project_name: Optional[str] = None
    location: Optional[str] = None
    function: Optional[str] = None
    scale: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status_id: Optional[int] = None


class ProjectCreate(ProjectBase):
    project_name: str


class ProjectUpdate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    id: int


class ProjectEmployee(BaseModel):
    employee_id: int
    project_id: int
    role: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None


class ProjectRequirement(BaseModel):
    project_id: int
    document_type_id: int

