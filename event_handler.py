import os

from dotenv import load_dotenv
from typing_extensions import override
from openai import AssistantEventHandler, OpenAI

# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.

import base64
from io import BytesIO
from PIL import Image

load_dotenv()
key = os.getenv("OPENAI_API_KEY")
if key is None:
    raise ValueError("API key is not set.")

client = OpenAI(api_key=key)


class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(f"DEBUG: Received delta: {delta}", flush=True)  # 記錄變更內容
        if delta.value:
            print(delta.value, end="", flush=True)
            # 檢查是否為 base64 圖片
            if "base64" in delta.value:
                self.handle_base64_image(delta.value)

    def on_tool_call_created(self, tool_call):
        print(f"\nDEBUG: Tool call detected: {tool_call.type} (id: {tool_call.id})", flush=True)
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'code_interpreter':
            print(f"DEBUG: Received code_interpreter delta: {delta}", flush=True)
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)
        elif delta.type == "file":
            # 偵測到文件附件
            file_id = delta.file_id
            print(f"DEBUG: Detected image file (File ID: {file_id})", flush=True)
            self.download_and_display_image(file_id)

    def on_run_step_created(self, run_step):
        print(f"DEBUG: Run step created: {run_step.type}", flush=True)

    def on_run_step_delta(self, delta, snapshot):
        print(f"DEBUG: Run step delta: {delta}", flush=True)

    def download_and_display_image(self, file_id):
        """ 下載並顯示 Assistant 回傳的圖片 """
        image_response = client.files.content(file_id=file_id)
        if image_response:
            try:
                image_bytes = image_response.read() if hasattr(image_response, "read") else bytes(image_response)
                with open("leak_detection_result.png", "wb") as f:
                    f.write(image_bytes)
                im = Image.open(BytesIO(image_bytes))
                im.show()
                print(f"圖片已成功顯示 (File ID: {file_id})")
            except Exception as e:
                print(f"無法處理圖片文件 (File ID: {file_id}): {e}")
        else:
            print(f"無法下載圖片 (File ID: {file_id})")

    def handle_base64_image(self, base64_string):
        """ 解析 Base64 圖片並顯示 """
        try:
            encoded_data = base64_string.split(",")[-1].strip()
            image_data = base64.b64decode(encoded_data)
            with open("leak_detection_base64.png", "wb") as f:
                f.write(image_data)
            im = Image.open(BytesIO(image_data))
            im.show()
            print("Base64 圖片已成功顯示")
        except Exception as e:
            print(f"無法解碼 Base64 圖片: {e}")



