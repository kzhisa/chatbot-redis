import os
import uuid
import redis
import json
from fastapi import FastAPI, Request
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

app = FastAPI()

# Redis設定
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=0, decode_responses=True)

# 会話履歴数
DEFAULT_MAX_MESSAGES = 4

# Langchain
unique_id = uuid.uuid4().hex[0:8]
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = f"Tracing Chatbot with FastAPI - {unique_id}"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY')

class RedisChatMessageHistory(BaseChatMessageHistory):
    """Redis を使用して会話履歴を保存するクラス。"""

    def __init__(self, session_id, max_messages=DEFAULT_MAX_MESSAGES):
        """
        初期化。

        Args:
            session_id (str): セッションID。
            max_messages (int, optional): 会話履歴の最大数。Defaults to DEFAULT_MAX_MESSAGES.
        """
        self.session_id = session_id
        self.max_messages = max_messages
        self.messages = []
        self.load_history()

    def load_history(self):
        """Redis から会話履歴を読み込む。"""
        history_data = redis_client.get(self.session_id)
        if history_data:
            loaded_messages = json.loads(history_data)
            self.messages = [self.message_from_dict(msg) for msg in loaded_messages]
        else:
            self.messages = []

    def save_history(self):
        """Redis に会話履歴を保存する。"""
        serialized_messages = [self.message_to_dict(msg) for msg in self.messages]
        redis_client.set(self.session_id, json.dumps(serialized_messages))
        redis_client.expire(self.session_id, 3600)  # セッションの有効期限を1時間に設定

    def add_message(self, message):
        """会話履歴にメッセージを追加する。"""
        if isinstance(message, BaseMessage):
            self.messages.append(message)
        else:
            self.messages.append(HumanMessage(content=message))
        # 会話履歴数を制限
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
        self.save_history()

    def get_messages(self):
        """会話履歴を取得する。"""
        return self.messages

    def clear(self):
        """会話履歴をクリアする。"""
        self.messages = []
        self.save_history()

    def message_to_dict(self, message: BaseMessage) -> dict:
        """メッセージを辞書に変換する。"""
        return {"type": message.type, "content": message.content}

    def message_from_dict(self, message_dict: dict) -> BaseMessage:
        """辞書からメッセージを作成する。"""
        if message_dict["type"] == "human":
            return HumanMessage(content=message_dict["content"])
        elif message_dict["type"] == "ai":
            return AIMessage(content=message_dict["content"])
        else:
            raise ValueError(f"Unknown message type: {message_dict['type']}")

# セッションIDごとの会話履歴の取得
def get_session_history(session_id: str) -> BaseChatMessageHistory:
    return RedisChatMessageHistory(session_id)

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

    # 応答を保存
    """
    redis_history = get_session_history(session_id)
    redis_history.add_message(HumanMessage(content=input_message))
    redis_history.add_message(AIMessage(content=response.content))
    """

    # 応答をJSON形式で返す
    return JSONResponse({"answer": response.content})