from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from . import models
from .models import Conversation, Message
from .schemas import ChatRequest, ChatResponse, HealthResponse


# Create database tables automatically when the application starts.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Support Assistant API",
    description="Backend API for the Smart Support Assistant",
    version="1.0.0",
)

# Allow the Vite frontend to communicate with the FastAPI backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    # Use an existing conversation if conversation_id was provided.
    if request.conversation_id is not None:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == request.conversation_id)
            .first()
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

    # Otherwise create a new conversation.
    else:
        conversation = Conversation()
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Save the user's message.
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )

    db.add(user_message)
    db.commit()

    # Day 11 uses an echo response.
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=request.message,
    )

    db.add(assistant_message)
    db.commit()

    return ChatResponse(
        conversation_id=conversation.id,
        message=request.message,
    )