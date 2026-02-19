from pydantic import BaseModel
from typing import List, Optional, Literal

class Structure(BaseModel):
    structure_id: str
    structure_type: Literal[
        "DIVISION", "SECTION", "PARAGRAPH",
        "LOOP", "FILE_OP", "CONDITIONAL"
    ]
    name: str
    line_range: List[int]
    description: str
    parent_id: Optional[str]

class StructureOutput(BaseModel):
    program_name: str
    language: str
    structures: List[Structure]
