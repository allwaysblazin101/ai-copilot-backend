# backend/tools/validator.py
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

class ToolResponse(BaseModel):
    status: str = Field(..., pattern="^(success|error|pending)$")
    message: str
    data: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None

    @classmethod
    def success(cls, message: str, data: Any = None):
        return cls(status="success", message=message, data=data)

    @classmethod
    def error(cls, message: str, code: str = "GENERIC_ERROR"):
        return cls(status="error", message=message, error_code=code)
