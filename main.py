import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime

from database import db, create_document, get_documents
from schemas import Video, ContactMessage

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory for uploaded videos
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
def read_root():
    return {"message": "Portfolio API running"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# Models for responses
class VideoOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    url: str
    mime_type: Optional[str]
    size_bytes: Optional[int]
    created_at: Optional[str] = None

# Video upload endpoint
@app.post("/api/videos", response_model=VideoOut)
async def upload_video(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None)
):
    # Save file to uploads directory
    file_ext = os.path.splitext(file.filename)[1]
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    safe_name = f"video_{ts}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    public_url = f"/uploads/{safe_name}"

    video_doc = Video(
        title=title,
        description=description,
        filename=safe_name,
        url=public_url,
        mime_type=file.content_type,
        size_bytes=len(contents)
    )
    try:
        inserted_id = create_document("video", video_doc)
    except Exception as e:
        # Cleanup saved file if DB fails
        try:
            os.remove(file_path)
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

    return VideoOut(
        id=inserted_id,
        title=video_doc.title,
        description=video_doc.description,
        url=public_url,
        mime_type=video_doc.mime_type,
        size_bytes=video_doc.size_bytes,
        created_at=datetime.utcnow().isoformat()
    )

# List videos endpoint
@app.get("/api/videos", response_model=List[VideoOut])
async def list_videos(limit: int = 50):
    try:
        docs = get_documents("video", {}, limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    out: List[VideoOut] = []
    for d in docs:
        out.append(VideoOut(
            id=str(d.get("_id")),
            title=d.get("title", "Untitled"),
            description=d.get("description"),
            url=d.get("url", ""),
            mime_type=d.get("mime_type"),
            size_bytes=d.get("size_bytes"),
            created_at=str(d.get("created_at")) if d.get("created_at") else None
        ))
    return out

# Contact endpoint - send email via Gmail SMTP or fallback store
class ContactPayload(BaseModel):
    name: str
    email: EmailStr
    message: str

@app.post("/api/contact")
async def send_contact(payload: ContactPayload):
    # Try to send email via Gmail SMTP if credentials exist
    gmail_user = os.getenv("GMAIL_USER")
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD")
    to_email = os.getenv("CONTACT_TO_EMAIL") or gmail_user

    saved_id = None
    try:
        saved_id = create_document("contactmessage", ContactMessage(**payload.model_dump()))
    except Exception:
        pass

    if gmail_user and gmail_app_password and to_email:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = gmail_user
        msg["To"] = to_email
        msg["Subject"] = f"New Contact from {payload.name}"
        body = f"Name: {payload.name}\nEmail: {payload.email}\n\nMessage:\n{payload.message}"
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gmail_user, gmail_app_password)
                server.sendmail(gmail_user, to_email, msg.as_string())
            return {"status": "sent", "saved_id": saved_id}
        except Exception as e:
            # If email fails, but we saved to DB, still return ok with warning
            return JSONResponse(status_code=202, content={"status": "saved_only", "warning": str(e), "saved_id": saved_id})

    # If no SMTP configured, at least store message
    if saved_id:
        return {"status": "saved_only", "saved_id": saved_id}
    else:
        raise HTTPException(status_code=500, detail="Email not configured and database unavailable.")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
