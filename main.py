from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage
import json

app = FastAPI()

BUCKET_NAME = "anktest"

class SessionRequest(BaseModel):
    user_id: str

# CORS: ブラウザ(GitHub Pages) → Cloud Run のため
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SessionRequest(BaseModel):
    user_id: str

@app.get("/")
def root():
    return {"message": "anktest-api is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/session")
def create_session(req: SessionRequest):

    user_id = req.user_id

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    blob_path = f"{user_id}/qa.json"
    blob = bucket.blob(blob_path)

    # 既に存在するか
    if not blob.exists():

        init_data = {
            "user_id": user_id,
            "records": []
        }

        blob.upload_from_string(
            json.dumps(init_data, ensure_ascii=False, indent=2),
            content_type="application/json"
        )

    return {
        "user_id": user_id,
        "status": "session ok"
    }
