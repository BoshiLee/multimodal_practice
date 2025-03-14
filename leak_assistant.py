import json
import os
import base64
import time

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from io import BytesIO
from parse_inp import parse_inp, save_to_json

# **1️⃣ 載入 API Key**
load_dotenv()
key = os.getenv("OPENAI_API_KEY")
if key is None:
    raise ValueError("API key is not set.")

client = OpenAI(api_key=key)

######################################################################
# 下載檔案函式
######################################################################
def download_file(file_id, output_path):
    """下載 OpenAI API 中的 file_id 檔案並儲存為 output_path"""
    try:
        response = client.files.content(file_id=file_id)
        file_content = response.read()
        with open(output_path, 'wb') as f:
            f.write(file_content)
        print(f"文件已成功下載並保存至 {output_path}")
    except Exception as e:
        print(f"下載文件時發生錯誤：{e}")


def download_sandbox_file(file_path, output_path):
    """下載 sandbox 路徑檔案 (例如 sandbox:/mnt/data/xxx)，解析其中的 file_id 後下載"""
    try:
        # sandbox:/mnt/data/... => 取得最後段
        file_id = file_path.split("/")[-1]  # 解析 sandbox 文件 ID
        response = client.files.content(file_id=file_id)
        file_content = response.read()
        with open(output_path, 'wb') as f:
            f.write(file_content)
        print(f"Sandbox 文件已成功下載並保存至 {output_path}")
    except Exception as e:
        print(f"下載 Sandbox 文件時發生錯誤：{e}")

######################################################################
# 讀取 system_prompt.md 作為 Assistant 的 instructions
######################################################################
with open("system_prompt.md", "r", encoding="utf-8") as file:
    system_prompt = file.read()

# **2️⃣ 創建 Assistant**
assistant = client.beta.assistants.create(
    name="Leak Detection Assistant",
    instructions=system_prompt,
    tools=[{"type": "code_interpreter"}],  # 重要！確保 Assistant 有權限解析數據
    model="gpt-4o"
)
print(f"Assistant Created: {assistant.id}")

######################################################################
# 解析 EPANET .inp 文件並打包成 JSON
######################################################################
file_path = "0401-13-01-12.inp"
parsed_data = parse_inp(file_path)
json_file_path = "parsed_network.json"
save_to_json(parsed_data, json_file_path)
print(f"JSON data saved to: {json_file_path}")

# 檢視 JSON
with open(json_file_path, "r", encoding="utf-8") as rj:
    raw_json = rj.read()
print("Parsed Data below (from JSON file):")
print(raw_json)

######################################################################
# 上傳 JSON 檔案給 Assistant
######################################################################
json_file_upload = client.files.create(
    file=open(json_file_path, "rb"),
    purpose="assistants"
)
print(f"JSON File Uploaded: {json_file_upload.id}")

######################################################################
# 建立對話環境（Thread），並帶上 JSON 檔案
######################################################################
thread = client.beta.threads.create(
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "這是從 EPANET .inp 文件解析出的管網數據，已打包為 JSON 檔案，請加以解析。\n"
                        "請找出可能的漏水區域，並繪製管網拓撲結構圖 (圖片附件或 Base64)。\n"
                        "若產生檔案，請使用 sandbox 路徑或附件返回也可以\n"
                    )
                }
            ],
            "attachments": [
                {
                    "file_id": json_file_upload.id,
                    "tools": [{"type": "code_interpreter"}]
                }
            ]
        }
    ]
)
print(f"Thread Created: {thread.id}")

######################################################################
# 啟動 Assistant (非串流) or 串流
######################################################################
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id
    # stream=True # 如要串流則加此參數
)
print(f"Run Created: {run.id}")

# 輪詢狀態
while True:
    run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
    print(f"Run Status: {run_status.status}")
    if run_status.status in ["completed", "failed", "cancelled"]:
        break
    time.sleep(5)

######################################################################
# 讀取最終回應  (示範解析 sandbox 路徑、base64)
######################################################################
print("\n--- Final Messages ---")
messages = client.beta.threads.messages.list(thread_id=thread.id)
sorted_messages = sorted(messages, key=lambda m: m.created_at)

for msg in sorted_messages:
    print(f"{msg.role}: {msg.content}")

    # 處理 sandbox 路徑檔案
    if hasattr(msg, 'content') and isinstance(msg.content, list):
        for content_block in msg.content:
            if hasattr(content_block, 'annotations'):
                for annotation in content_block.annotations:
                    if annotation.type == 'file_path' and 'sandbox' in annotation.text:
                        sandbox_path = annotation.text.split(':')[-1]
                        output_file = os.path.basename(sandbox_path)
                        download_sandbox_file(sandbox_path, output_file)
                        print(f"已成功下載 Sandbox 文件: {output_file}")
            # 處理圖片附件
            if hasattr(content_block, 'image_file') and content_block.image_file:
                image_file_id = content_block.image_file.file_id
                image_response = client.files.content(file_id=image_file_id)
                if image_response:
                    image_bytes = None
                    if hasattr(image_response, 'read'):
                        image_bytes = image_response.read()
                    else:
                        try:
                            image_bytes = bytes(image_response)
                        except TypeError:
                            if isinstance(image_response, str):
                                image_bytes = image_response.encode("utf-8")

                    if image_bytes:
                        with open("leak_detection_result.png", "wb") as outimg:
                            outimg.write(image_bytes)
                        im = Image.open(BytesIO(image_bytes))
                        im.show()
                        print(f"圖片已成功顯示 (File ID: {image_file_id})")
                    else:
                        print(f"無法取得圖片 bytes (File ID: {image_file_id})")
                else:
                    print(f"無法下載圖片 (File ID: {image_file_id})")

    # 若 Assistant 回傳 Base64 圖片
    if isinstance(msg.content, str) and "base64" in msg.content:
        try:
            encoded_data = msg.content.split(",")[-1].strip()
            image_data = base64.b64decode(encoded_data)
            with open("leak_detection_base64.png", "wb") as f:
                f.write(image_data)
            im = Image.open(BytesIO(image_data))
            im.show()
        except Exception as e:
            print(f"無法解碼 base64 圖片: {e}")
