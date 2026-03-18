from datetime import date
from typing import Optional, List, Any

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
    tree_data: Optional[Any] = None


class ProjectList(BaseModel):
    projects: list[ProjectOut]


class ProjectEmployeeCreate(BaseModel):
    employee_id: int
    role: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None


class ProjectEmployeeOut(BaseModel):
    employee_id: int
    project_id: int
    role: Optional[str] = None
    start_date: date
    end_date: Optional[date] = None
    full_name: Optional[str] = None
    employee_code: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None


class ProjectEmployeeList(BaseModel):
    members: list[ProjectEmployeeOut]


class ProjectRequirementUpdate(BaseModel):
    document_type_ids: list[int]


class ProjectRequirementOut(BaseModel):
    project_id: int
    document_type_id: int
    type_name: Optional[str] = None


class ProjectRequirementList(BaseModel):
    requirements: list[ProjectRequirementOut]


class ProjectTreeUpdate(BaseModel):
    tree_data: Any


class ProjectEmployeeBatchCreate(BaseModel):
    employees: list[ProjectEmployeeCreate]


