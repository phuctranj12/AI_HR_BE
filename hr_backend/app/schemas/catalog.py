from pydantic import BaseModel


class DocumentTypeCreate(BaseModel):
    type_name: str


class DocumentTypeOut(BaseModel):
    id: int
    type_name: str


class DocumentTypeList(BaseModel):
    document_types: list[DocumentTypeOut]


class StatusOut(BaseModel):
    id: int
    status_name: str


class StatusList(BaseModel):
    statuses: list[StatusOut]
