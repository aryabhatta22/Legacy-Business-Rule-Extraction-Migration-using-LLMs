from typing import List, Literal
from pydantic import BaseModel

class Evidence(BaseModel):
    source_structures: List[str]
    source_lines: List[int]

class BusinessRule(BaseModel):
    rule_id: str
    rule_statement: str
    rule_category: Literal[
        "BUSINESS", "TECHNICAL", "ERROR_HANDLING"
    ]
    domain: str
    evidence: Evidence
    confidence: Literal["high", "medium", "low"]
    assumptions: List[str]

class BusinessLogicOutput(BaseModel):
    program_name: str
    business_rules: List[BusinessRule]
