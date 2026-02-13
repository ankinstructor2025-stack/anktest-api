from openai import OpenAI
from fastapi import FastAPI, Form, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage
import json
import os

app = FastAPI()

BUCKET_NAME = "anktest"

def _build_qa_prompt(dialogue_text: str) -> str:
    return (
        "次の対話データから、ユーザーの質問と回答のペア(QA)を抽出してください。\n"
        "出力は必ず JSON のみ。コードブロックは禁止。\n"
        "形式:\n"
        "[\n"
        "  {\"q\": \"質問\", \"a\": \"回答\"}\n"
        "]\n\n"
        "対話データ:\n"
        f"{dialogue_text}\n"
    )

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

@app.post("/v1/qa_build")
async def qa_build(
    user_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    既存の「アップロード」は維持。
    追加で「QA生成だけ」を実施し、レスポンスに qa を載せる（保存はしない）。
    """
    # ---- 既存：GCSアップロード（そのまま） ----
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    object_path = f"{user_id}/upload_files/{file.filename}"
    blob = bucket.blob(object_path)

    data = await file.read()
    blob.upload_from_string(
        data,
        content_type=file.content_type or "application/octet-stream"
    )

    # ---- 追加：QA生成だけ（保存なし） ----
    if not os.environ.get("OPENAI_API_KEY"):
        # アップロードは成功しているので、ここは 500 にせず状態を返す
        return {
            "status": "uploaded_but_qa_skipped",
            "reason": "OPENAI_API_KEY is not set",
            "user_id": user_id,
            "upload_file": f"upload_files/{file.filename}",
            "gcs_object": object_path
        }

    try:
        # 文字化けしても止めずに続行（最低限）
        try:
            dialogue_text = data.decode("utf-8")
        except UnicodeDecodeError:
            dialogue_text = data.decode("utf-8", errors="replace")

        oa = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        prompt = _build_qa_prompt(dialogue_text)

        res = oa.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        content = res.choices[0].message.content or ""

        # JSONとして返せる形だけ保証（失敗してもアップロードは壊さない）
        qa_list = json.loads(content)
        if not isinstance(qa_list, list):
            raise ValueError("QA JSON is not a list")

        return {
            "status": "uploaded_and_qa_generated",
            "user_id": user_id,
            "upload_file": f"upload_files/{file.filename}",
            "gcs_object": object_path,
            "qa": qa_list
        }

    except Exception as e:
        # 失敗しても「アップロード済み」は維持して返す
        return {
            "status": "uploaded_but_qa_failed",
            "user_id": user_id,
            "upload_file": f"upload_files/{file.filename}",
            "gcs_object": object_path,
            "error": str(e),
        }

@app.get("/v1/openai_echo")
def openai_echo():

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "echo test"}
        ]
    )

    return {
        "ok": True,
        "reply": res.choices[0].message.content
    }
