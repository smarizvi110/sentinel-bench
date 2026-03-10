from pydantic import BaseModel, Field
from typing import Literal, List


class ConstitutionalViolation(BaseModel):
    section: str = Field(..., description="The specific constitutional section violated (if any).")
    reasoning: str = Field(..., description="Step-by-step legal logic linking the proposal text to the rule.")


class Verdict(BaseModel):
    ruling: Literal["UPHOLD", "STRIKE_DOWN"] = Field(..., description="The final binary judgment.")
    violations: List[ConstitutionalViolation] = Field(default_factory=list, description="List of violations. Must be empty if UPHOLD.")
    # Renamed to clarify this is the model's self-reported claim
    elicited_confidence: float = Field(..., description="Self-reported confidence score from 0.0 to 1.0.")
