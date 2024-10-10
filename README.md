## Chatbot with LangChain and FastAPI

このリポジトリは、LangChain と FastAPI を使用して構築されたチャットボットのサンプルコードを提供します。

### 概要

このチャットボットは、以下の機能を提供します。

- APIでテキスト入力（質問）を受け付けます。
- LangChain を使用して、入力テキストを処理し、適切な応答を生成します。
- FastAPI を使用して、REST API を介してユーザーと通信します。
- 会話履歴を Redis に保存することで、セッション間で会話履歴を保持します。

### ファイル構成

- `chatbot.py`: プロセス内で会話履歴を管理するチャットボット
- `chatbot_redis.py`: Redis を使用して会話履歴を保存する機能を実装したチャットボット
- `api_test.http`: API テスト用の HTTP リクエストファイル。
- `Pipfile`: プロジェクトの依存関係を定義したファイル。

### 実行方法

1. `Pipfile` に記載されている依存関係をインストールします。
```bash
pip install -r requirements.txt
```
2. Redis サーバーを起動します。
3. 環境変数 `GOOGLE_API_KEY` に Google Gemini の API キーを設定します。
4. langSmithを利用する場合は、環境変数 `LANGCHAIN_API_KEY` に LangChain API キーを設定します。
5. `chatbot.py` または `chatbot_redis.py` を実行します。
```bash
uvicorn --port 8880 --app-dir . chatbot:app
uvicorn --port 8880 --app-dir . --workers 3 chatbot_redis:app
```
5. `api_test.http` ファイルに記載されている HTTP リクエストを送信して、チャットボットをテストします。

### 使用例

```
POST http://localhost:8880/chat HTTP/1.1
Content-Type: application/json

{
    "session_id": "test_session_1",
    "message": "こんにちは。私はネコを飼っています。ペットの名前はキキです。きれいな黒猫です。"
}
```

### 注意点

- このコードは、LangChain と FastAPI の基本的な使用方法を示すサンプルコードです。
- 実用的なチャットボットを構築するには、より高度な機能を追加する必要があります。

