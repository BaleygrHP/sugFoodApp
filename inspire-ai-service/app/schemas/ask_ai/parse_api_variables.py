from typing import Any, Optional
from pydantic import BaseModel, Field

from app.models.ask_ai.variable import Variable


class ParseApiVariablesDto(BaseModel):
    language: str = Field("English", description="Language of output variables' description")
    name: str = Field(..., description="Name of the API")
    description: str = Field(..., description="Description of the API")
    parameters: Optional[dict[str, str]] = Field(None, description="API Parameters")
    body: Optional[dict[str, Any]] = Field(None, description="API Body")
    current_variables: Optional[list[Variable]] = Field(None, description="Current variables")
