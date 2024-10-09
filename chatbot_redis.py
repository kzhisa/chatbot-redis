import os
import uuid
import redis
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_redis import RedisChatMessageHistory

app = FastAPI()

# Redis設定
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# 会話履歴数
DEFAULT_MAX_MESSAGES = 4

# Langchain
unique_id = uuid.uuid4().hex[0:8]
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = f"Tracing Chatbot with FastAPI - {unique_id}"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY')

# セッションIDごとの会話履歴の取得
def get_message_history(session_id: str) -> BaseChatMessageHistory:
    return RedisChatMessageHistory(
        session_id,
        redis_url=REDIS_URL
    )

# プロンプトテンプレートで会話履歴を追加
prompt_template = ChatPromptTemplate.from_messages(
    [
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}"),
    ]
)

@app.post("/chat")
async def chat(request: Request):
    # リクエストボディからセッションIDと入力メッセージを取得
    body = await request.json()
    session_id = body.get("session_id")
    input_message = body.get("message")

    # LLM
    chat_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.5)

    # Runnableの準備
    runnable = prompt_template | chat_model

    # RunnableをRunnableWithMessageHistoryでラップ
    runnable_with_history = RunnableWithMessageHistory(
        runnable,
        get_message_history,
        input_messages_key="input",
        history_messages_key="history"
    )

    # プロンプトテンプレートに基づいて応答を生成
    response = runnable_with_history.invoke(
        {"input": input_message},
        config={"configurable": {"session_id": session_id}}
    )

    # 応答をJSON形式で返す
    return JSONResponse({"answer": response.content})