from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime

class CreateGuildRequest(BaseModel):
    character_id: str
    name:         str
    description:  str = ""

class GuildResponse(BaseModel):
    id:                UUID
    name:              str
    description:       str
    leader_id:         UUID
    level:             int
    max_members:       int
    contribution_pool: int
    member_count:      int = 0
    created_at:        datetime

    class Config:
        from_attributes = True

class GuildMemberResponse(BaseModel):
    character_id: UUID
    character_name: str = ""
    role:         str
    contribution: int
    joined_at:    datetime

    class Config:
        from_attributes = True

class JoinGuildRequest(BaseModel):
    character_id: str
    guild_id:     str