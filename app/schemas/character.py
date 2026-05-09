from pydantic import BaseModel
from uuid import UUID

class CreateCharacterRequest(BaseModel):
    name: str
    class_id: str  # "WARRIOR", "GUARDIAN", "RANGER", etc.

class CharacterResponse(BaseModel):
    id:            UUID
    name:          str
    class_id:      str
    level:         int
    soul_level:    int
    current_exp:   int
    gold:          int
    gems:          int
    current_map_id: int

    class Config:
        from_attributes = True