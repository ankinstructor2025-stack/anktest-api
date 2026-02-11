from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# --- CORS（ブラウザ→Cloud Run用） ---
# いったん教材の検証用として * を許可（動作確認後に絞る）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],   # OPTIONS を含める
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "anktest-api is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/session")
def create_session(req: SessionRequest):
    # ここでは「受け取って返す」だけ（最小構成）
    # 次のステップで、この user_id を使ってGCS管理に進む
    return {
        "user_id": req.user_id,
        "status": "session ok"
    }
