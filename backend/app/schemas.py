from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: int | None = Field(
        default=None,
        description="Existing conversation ID. Leave empty to create a new conversation."
    )
    message: str = Field(
        ...,
        min_length=1,
        description="The user's chat message."
    )


class ChatResponse(BaseModel):
    conversation_id: int
    message: str


class HealthResponse(BaseModel):
    status: str