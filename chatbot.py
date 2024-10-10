import os
import uuid
import time

from fastapi import FastAPI, Request
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi.responses import JSONResponse

app = FastAPI()

# 会話履歴数
DEFAULT_MAX_MESSAGES = 10

# Langchain
unique_id = uuid.uuid4().hex[0:8]
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = f"Tracing Simple Chatbot - {unique_id}"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY')


# 会話履歴数をmax_lengthに制限するLimitedChatMessageHistoryクラス
class LimitedChatMessageHistory(ChatMessageHistory):

    # 会話履歴の保持数
    max_messages: int = DEFAULT_MAX_MESSAGES

    def __init__(self, max_messages=DEFAULT_MAX_MESSAGES):
        super().__init__()
        self.max_messages = max_messages

    def add_message(self, message):
        super().add_message(message)
        # 会話履歴数を制限
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]

    def get_messages(self):
        return self.messages


# 会話履歴のストア
store = {}

# セッションIDごとの会話履歴の取得
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = LimitedChatMessageHistory()
    return store[session_id]


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
    chat_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)

    # Runnableの準備
    runnable = prompt_template | chat_model

    # RunnableをRunnableWithMessageHistoryでラップ
    runnable_with_history = RunnableWithMessageHistory(
        runnable=runnable,
        get_session_history=get_session_history,
        input_messages_key="input",
        history_messages_key="history"
    )

    # プロンプトテンプレートに基づいて応答を生成
    response = runnable_with_history.invoke(
        {"input": input_message},
        config={"configurable": {"session_id": session_id}}
    )

    # Sleep - 2秒停止
    time.sleep(2)

    # 応答をJSON形式で返す
    return JSONResponse({"answer": response.content})
