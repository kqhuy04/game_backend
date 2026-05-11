from pydantic import BaseModel, field_validator
from uuid import UUID

VALID_CLASSES = [
    "WARRIOR", "GUARDIAN", "RANGER", "PYROMANCER",
    "ROGUE", "FOREST_SPIRIT", "WIZARD", "PRIEST", "WIND_SPIRIT"
]

class CreateCharacterRequest(BaseModel):
    name:     str
    class_id: str

    @field_validator("name")
    def name_valid(cls, v):
        if len(v) < 2 or len(v) > 20:
            raise ValueError("Name must be 2-20 characters")
        return v.strip()

    @field_validator("class_id")
    def class_valid(cls, v):
        if v.upper() not in VALID_CLASSES:
            raise ValueError(f"Invalid class. Choose from: {VALID_CLASSES}")
        return v.upper()

class CharacterResponse(BaseModel):
    id:             UUID
    name:           str
    class_id:       str
    level:          int
    soul_level:     int
    current_exp:    int
    gold:           int
    gems:           int
    current_map_id: int

    class Config:
        from_attributes = True