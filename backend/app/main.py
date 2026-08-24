from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import os
import google.generativeai as genai
from dotenv import load_dotenv

from .database import Base, engine, get_db
from . import models
from .models import Conversation, Message
from .schemas import ChatRequest, ChatResponse, HealthResponse


# Load environment variables.
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are a helpful and friendly customer support assistant."
)

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not configured.")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-3.6-flash",
    system_instruction=SYSTEM_PROMPT,
)


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

    # Get the previous 20 messages from the conversation.
    history_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )

    history_messages.reverse()

    # Build the conversation history for Gemini.
    history = []

    for message in history_messages:
        role = "user" if message.role == "user" else "model"

        history.append(
            {
                "role": role,
                "parts": [message.content],
            }
        )

    # Generate a response using Gemini.
    try:
        chat_session = model.start_chat(history=history)

        response = chat_session.send_message(request.message)

        assistant_content = response.text

    except Exception as e:
        print("GEMINI ERROR:", repr(e))
        raise HTTPException(
            status_code=502,
            detail="LLM service is unavailable.",
        )

    # Save the user's message.
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )

    db.add(user_message)
    db.commit()

    # Save the assistant's response.
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content,
    )

    db.add(assistant_message)
    db.commit()

    # Return the assistant's response.
    return ChatResponse(
        conversation_id=conversation.id,
        message=assistant_content,
    )