from pydantic import BaseModel, ConfigDict


class ValidationError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    object_type: str
    object_id: str | None
    field: str | None
    related_id: str | None
