# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.database import Base, engine, SessionLocal
from app import models
from fastapi import UploadFile, File, HTTPException,Depends
from sqlalchemy import func
from .models import Document, DocumentChunk
from .document_utils import extract_text, create_chunks, create_embeddings
Base.metadata.create_all(bind=engine)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI(
    title="Smart Support Assistant",
    description="API for AI-powered customer support",
    version="1.0.0"
)

# Add CORS middleware to allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):

    db = SessionLocal()

    if req.conversation_id is not None:
        conversation = db.query(models.Conversation).filter(
            models.Conversation.id == req.conversation_id
        ).first()
    else:
        conversation = None

    if conversation is None:
        conversation = models.Conversation()
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        message = models.Message(
            conversation_id=conversation.id,
            role="user",
            content=req.message
        )

    db.add(message)
    db.commit()

    assistant_message = models.Message(
        conversation_id=conversation.id,
        role="assistant",
        content=f"Echo: {req.message}"
    )
    db.add(assistant_message)
    db.commit()

    return ChatResponse(
        reply=f"Echo: {req.message}",
        conversation_id=str(conversation.id)
    )
@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    db=Depends(get_db)
):

    filename = file.filename

    if not filename.lower().endswith((".txt", ".pdf")):
        raise HTTPException(
            status_code=400,
            detail="Only .txt and .pdf files are supported"
        )

    file_bytes = await file.read()

    try:
        text = extract_text(filename, file_bytes)
        chunks = create_chunks(text)
        embeddings = create_embeddings(chunks)

        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="The uploaded document contains no readable text"
            )

        existing_document = (
            db.query(Document)
            .filter(Document.filename == filename)
            .first()
        )

        if existing_document:
            db.delete(existing_document)
            db.commit()

        document = Document(filename=filename)

        db.add(document)
        db.commit()
        db.refresh(document)

        for index, (chunk, embedding) in enumerate(
            zip(chunks, embeddings)
        ):
            document_chunk = DocumentChunk(
                document_id=document.id,
                content=chunk,
                chunk_index=index,
                embedding=embedding,
            )

            db.add(document_chunk)

        db.commit()

        return {
            "message": "Document uploaded successfully",
            "filename": filename,
            "chunks": len(chunks),
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Document processing failed: {str(e)}"
        )

@app.get("/documents")
def list_documents(db=Depends(get_db)):
    documents = (
        db.query(
            Document.id,
            Document.filename,
            Document.created_at,
            func.count(DocumentChunk.id).label("chunk_count")
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
        .order_by(Document.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(document.id),
            "filename": document.filename,
            "created_at": document.created_at,
            "chunk_count": document.chunk_count,
        }
        for document in documents
    ]
@app.get("/documents/{document_id}")
def get_document(document_id: str, db=Depends(get_db)):
    document = db.query(Document).filter(
        Document.id == document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    chunk_count = db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id
    ).count()

    return {
        "id": str(document.id),
        "filename": document.filename,
        "created_at": document.created_at,
        "chunk_count": chunk_count
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
