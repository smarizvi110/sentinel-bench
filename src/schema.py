from pydantic import BaseModel, Field
from typing import Literal, List, Optional


class ConstitutionalViolation(BaseModel):
    section: str = Field(..., description="The specific constitutional section violated (if any).")
    reasoning: str = Field(..., description="Step-by-step legal logic linking the proposal text to the rule.")


class Verdict(BaseModel):
    ruling: Literal["UPHOLD", "STRIKE_DOWN", "INVALID"] = Field(..., description="The final binary judgment, or INVALID if generation failed.")
    violations: List[ConstitutionalViolation] = Field(default_factory=list, description="List of violations. Must be empty if UPHOLD.")
    # This is the model's self-reported claim
    elicited_confidence: Optional[float] = Field(..., description="Self-reported confidence score from 0.0 to 1.0.")
