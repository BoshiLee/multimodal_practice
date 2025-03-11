import time
import os
from dotenv import load_dotenv
from openai import OpenAI

# **1️⃣ 載入 API Key**
load_dotenv()
key = os.getenv("OPENAI_API_KEY")
if key is None:
    raise ValueError("API key is not set.")

client = OpenAI(api_key=key)

# **2️⃣ 創建 Assistant**
assistant = client.beta.assistants.create(
    name="Math Tutor",
    instructions="You are a personal math tutor. Solve math problems using code execution only.",
    tools=[{"type": "code_interpreter"}],
    model="gpt-4o",
)

# **3️⃣ 創建 Thread**
thread = client.beta.threads.create()

# **4️⃣ 發送訊息**
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="I need to solve the equation `3x + 11 = 14`. Can you help me?"
)

print(f"DEBUG: Running thread_id={thread.id}, assistant_id={assistant.id}", flush=True)

# **5️⃣ 建立 Run**
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
    instructions="Solve the equation using code execution only. Return the numerical result of x.",
)

print(f"DEBUG: Run created. Run ID: {run.id}", flush=True)

# **6️⃣ 輪詢 Run 狀態，直到完成**
while True:
    run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    print(f"DEBUG: Run status: {run_status.status}", flush=True)

    if run_status.status in ["completed", "failed", "cancelled"]:
        break  # 退出輪詢

    time.sleep(2)  # 每 2 秒檢查一次

# **7️⃣ 檢查錯誤資訊**
if run_status.status == "failed":
    print(f"ERROR: Run failed. Reason: {run_status.last_error}")

    # **8️⃣ 嘗試用 `stream()`**
    print("\nTrying `stream()` method for debugging...\n")
    from event_handler import EventHandler

    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="Solve the equation using the code interpreter only. Run Python and return the result.",
        event_handler=EventHandler(),
    ) as stream:
        print("DEBUG: Streaming started...", flush=True)
        stream.until_done()
        print("DEBUG: Streaming completed.", flush=True)

elif run_status.status == "completed":
    print("\nDEBUG: Run completed. Fetching messages...\n")
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    for msg in messages.data[::-1]:
        print(f"Assistant: {msg.content[0].text.value}")
