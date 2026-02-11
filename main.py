from fastapi import FastAPI

app = FastAPI()

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
