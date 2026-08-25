# backend/app/main.py
# Day 16 Individual Feature - Document Summary
# Author: Akanksha Panigrahi
import os
import json
from fastapi.responses import JSONResponse
from app.prompts.summary_prompt import SUMMARY_PROMPT

from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func

from google import genai

from app.database import Base, engine, SessionLocal
from app import models
from .models import Document, DocumentChunk
from .document_utils import extract_text, create_chunks, create_embeddings


# --------------------------------------------------
# Load environment variables
# --------------------------------------------------

load_dotenv()


# --------------------------------------------------
# Create database tables
# --------------------------------------------------

Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# Configure Gemini
# --------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. "
        "Please check your backend/.env file."
    )

client = genai.Client(
    api_key=GEMINI_API_KEY
)


# --------------------------------------------------
# Database dependency
# --------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# --------------------------------------------------
# FastAPI application
# --------------------------------------------------

app = FastAPI(
    title="Smart Support Assistant",
    description="API for AI-powered customer support",
    version="1.0.0"
)


# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000"
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# Request / Response Models
# --------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str

class SummaryRequest(BaseModel):
    document_id: str


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# RAG CHAT
# --------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):

    db = SessionLocal()

    try:

        # ------------------------------------------
        # Find existing conversation
        # ------------------------------------------

        if req.conversation_id:

            conversation = (
                db.query(models.Conversation)
                .filter(
                    models.Conversation.id == req.conversation_id
                )
                .first()
            )

        else:

            conversation = None


        # ------------------------------------------
        # Create a new conversation
        # ------------------------------------------

        if conversation is None:

            conversation = models.Conversation()

            db.add(conversation)
            db.commit()
            db.refresh(conversation)


        # ------------------------------------------
        # Save user's message
        # ------------------------------------------

        user_message = models.Message(
            conversation_id=conversation.id,
            role="user",
            content=req.message
        )

        db.add(user_message)
        db.commit()


        # ------------------------------------------
        # Create query embedding
        # ------------------------------------------

        question_embedding = create_embeddings(
            [req.message]
        )[0]


        # ------------------------------------------
        # Number of chunks to retrieve
        # ------------------------------------------

        top_k = int(
            os.getenv(
                "RAG_TOP_K",
                "3"
            )
        )


        # ------------------------------------------
        # Retrieve relevant chunks
        # ------------------------------------------

        chunks = (
            db.query(DocumentChunk)
            .order_by(
                DocumentChunk.embedding.cosine_distance(
                    question_embedding
                )
            )
            .limit(top_k)
            .all()
        )


        # ------------------------------------------
        # No documents available
        # ------------------------------------------

        if not chunks:

            answer = (
                "Not found in the uploaded documents."
            )

        else:

            # --------------------------------------
            # Combine retrieved chunks
            # --------------------------------------

            context = "\n\n".join(
                chunk.content
                for chunk in chunks
            )


            # --------------------------------------
            # Grounded RAG prompt
            # --------------------------------------

            prompt = f"""
You are a helpful customer support assistant.

You MUST answer the user's question ONLY using
the information provided in the document context.

DOCUMENT CONTEXT:
{context}

USER QUESTION:
{req.message}

IMPORTANT RULE:
If the answer is not present in the document context,
reply exactly:

Not found in the uploaded documents.

Do not use outside knowledge.
"""


            # --------------------------------------
            # Generate Gemini response
            # --------------------------------------

            try:

                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )

                answer = response.text.strip()

            except Exception as e:

                raise HTTPException(
                    status_code=502,
                    detail=f"LLM service unavailable: {str(e)}"
                )


        # ------------------------------------------
        # Save assistant response
        # ------------------------------------------

        assistant_message = models.Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer
        )

        db.add(assistant_message)
        db.commit()


        # ------------------------------------------
        # Return response
        # ------------------------------------------

        return ChatResponse(
            reply=answer,
            conversation_id=str(
                conversation.id
            )
        )


    finally:

        db.close()


# --------------------------------------------------
# DOCUMENT UPLOAD
# --------------------------------------------------

@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db=Depends(get_db)
):

    filename = file.filename


    # ----------------------------------------------
    # Validate file type
    # ----------------------------------------------

    if not filename.lower().endswith(
        (".txt", ".pdf")
    ):

        raise HTTPException(
            status_code=400,
            detail="Only .txt and .pdf files are supported"
        )


    file_bytes = await file.read()


    try:

        # ------------------------------------------
        # Extract document text
        # ------------------------------------------

        text = extract_text(
            filename,
            file_bytes
        )


        # ------------------------------------------
        # Create chunks
        # ------------------------------------------

        chunks = create_chunks(
            text
        )


        # ------------------------------------------
        # Make sure document contains text
        # ------------------------------------------

        if not chunks:

            raise HTTPException(
                status_code=400,
                detail="The uploaded document contains no readable text"
            )


        # ------------------------------------------
        # Create embeddings
        # ------------------------------------------

        embeddings = create_embeddings(
            chunks
        )


        # ------------------------------------------
        # Check whether document already exists
        # ------------------------------------------

        existing_document = (
            db.query(Document)
            .filter(
                Document.filename == filename
            )
            .first()
        )


        # ------------------------------------------
        # Delete old version
        # ------------------------------------------

        if existing_document:

            db.delete(
                existing_document
            )

            db.commit()


        # ------------------------------------------
        # Create document record
        # ------------------------------------------

        document = Document(
            filename=filename
        )

        db.add(document)
        db.commit()
        db.refresh(document)


        # ------------------------------------------
        # Store chunks and embeddings
        # ------------------------------------------

        for index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings)
        ):

            document_chunk = DocumentChunk(
                document_id=document.id,
                content=chunk,
                chunk_index=index,
                embedding=embedding
            )

            db.add(document_chunk)


        db.commit()


        # ------------------------------------------
        # Return upload result
        # ------------------------------------------

        return {
            "message": "Document uploaded successfully",
            "filename": filename,
            "chunks": len(chunks)
        }


    except HTTPException:

        raise


    except Exception as e:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )

# --------------------------------------------------
# DOCUMENT SUMMARY FEATURE
# Author: Akanksha
# --------------------------------------------------

@app.post("/documents/summary")
def generate_document_summary(
    request: SummaryRequest,
    db=Depends(get_db)
):

    # Find the requested document
    document = (
        db.query(Document)
        .filter(Document.id == request.document_id)
        .first()
    )

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # Get all chunks belonging to this document
    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id
        )
        .order_by(DocumentChunk.chunk_index)
        .all()
    )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No document content found"
        )

    # Combine chunks into one document
    document_text = "\n\n".join(
        chunk.content
        for chunk in chunks
    )

    try:
        # Build the prompt
        prompt = SUMMARY_PROMPT.format(
            text=document_text
        )

        # Call Gemini
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        raw_response = response.text.strip()

        # Remove markdown code fences if Gemini adds them
        if raw_response.startswith("```json"):
            raw_response = raw_response[7:]

        if raw_response.startswith("```"):
            raw_response = raw_response[3:]

        if raw_response.endswith("```"):
            raw_response = raw_response[:-3]

        raw_response = raw_response.strip()

        # Parse JSON
        try:
            result = json.loads(raw_response)

        except json.JSONDecodeError:
            raise HTTPException(
                status_code=502,
                detail="AI returned invalid JSON. Please try again."
            )

        # Make sure the required fields exist
        required_fields = [
            "title",
            "summary",
            "key_points",
            "keywords"
        ]

        if not all(
            field in result
            for field in required_fields
        ):
            raise HTTPException(
                status_code=502,
                detail="AI returned an invalid summary format."
            )

        return result

    except HTTPException:
        raise

    except Exception as e:
        print("SUMMARY ERROR:", repr(e))

        raise HTTPException(
            status_code=502,
            detail=f"Unable to generate document summary: {str(e)}"
    )


# --------------------------------------------------
# LIST DOCUMENTS
# --------------------------------------------------

@app.get("/documents")
def list_documents(
    db=Depends(get_db)
):

    documents = (
        db.query(
            Document.id,
            Document.filename,
            Document.created_at,
            func.count(
                DocumentChunk.id
            ).label("chunk_count")
        )
        .outerjoin(
            DocumentChunk,
            Document.id == DocumentChunk.document_id
        )
        .group_by(
            Document.id,
            Document.filename,
            Document.created_at
        )
        .order_by(
            Document.created_at.desc()
        )
        .all()
    )


    return [
        {
            "id": str(document.id),
            "filename": document.filename,
            "created_at": document.created_at,
            "chunk_count": document.chunk_count
        }
        for document in documents
    ]


# --------------------------------------------------
# GET SINGLE DOCUMENT
# --------------------------------------------------

@app.get("/documents/{document_id}")
def get_document(
    document_id: str,
    db=Depends(get_db)
):

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id
        )
        .first()
    )


    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )


    chunk_count = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id == document.id
        )
        .count()
    )


    return {
        "id": str(document.id),
        "filename": document.filename,
        "created_at": document.created_at,
        "chunk_count": chunk_count
    }


# --------------------------------------------------
# Run directly
# --------------------------------------------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )