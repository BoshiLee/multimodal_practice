from typing_extensions import override
from openai import AssistantEventHandler


# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.

class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(f"DEBUG: Received delta: {delta}", flush=True)  # 記錄變更內容
        if delta.value:
            print(delta.value, end="", flush=True)

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

    def on_run_step_created(self, run_step):
        print(f"DEBUG: Run step created: {run_step.type}", flush=True)

    def on_run_step_delta(self, delta, snapshot):
        print(f"DEBUG: Run step delta: {delta}", flush=True)


