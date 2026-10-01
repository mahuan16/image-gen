from agno.agent import Agent
from agno.models.ollama import Ollama
from agno.tools.mcp import MCPTools
from agno.tools.mcp import MultiMCPTools
from contextlib import asynccontextmanager
from contextlib import AsyncExitStack

import os
import re
import asyncio
import requests


MCP_URL = "https://postrhinal-arlinda-undelightful.ngrok-free.dev/sse"
HELLO_MCP_URL = "http://localhost:8002/sse"

MCP_SERVERS = [
    {"name": "Image Generation", "url": MCP_URL, "enabled": True, "instruct":""" Important rules:

            1. The system remembers the current girl image, outfit image, and prompt.
            - The user does NOT need to resend them every time.
            - If the user asks to generate an image without providing new images, use the currently stored values

            2. The generate_image tool can both:
            - use the currently stored values, or
            - update the stored prompt / girl image / outfit image if the user provides new ones (they are ALL strings)

            3. Do not ask the user for a girl image or outfit image unless they explicitly want to change one.
            - If the user does not provide a link or file, keep the current image values and just change the prompt to their message
            - If the user only gives a new outfit image (either a URL or file), keep the current girl file  and prompt
            - If the user only gives a new girl image (either a URL or file), keep the current outfit file and prompt

            4. When the user asks to make or generate an image:
            - Call generate_image directly
            - Pass only the values the user wants to change
            - Otherwise use the default values and do not ask the user for further information

            5. After generate_image returns a task_id, use get_image_result when the user asks to check progress or see the result.

            6. Use reset_to_defaults only if the user explicitly asks to reset everything.

            7. Do not explain which tool should be used unless the user asks.
            - Prefer calling the tool directly

            Examples:
            - If the user says "generate an image of her in a blue dress":
            call generate_image with the new prompt = "generate an image of her in a blue dress" only.
            Since no images were provided, just change the prompt.
            - If the user says "change the outfit image to this URL":
            call generate_image with outfitImg equal to the provided URL.
            - If the user says "generate again":
            use the currently remembered values and call generate_image without asking for images again.
            - If the user says "reset everything":
            call reset_to_defaults.
            - If the user asks you to check the image progress, call get_image_result"""},
    {"name":"Hello World", "url": HELLO_MCP_URL, "enabled": True, "instruct": """You have access to the say_hello tool. It accepts a string as a parameter, and the function will say hello to the parameter. only use if the user asks you to say hello."""},
]


def path_to_url(file_path: str) -> str:

    with open(file_path, "rb") as f:
        response = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",
            data={"reqtype": "fileupload", "time": "24h"},
            files={"fileToUpload": f}
        )
    response.raise_for_status()
    return response.text.strip()


def check_for_path(text: str) -> str:
    # will check for path
    path_pattern = r'[A-Za-z]?:?[/\\][\w/\\.\-]+'
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

    # callback helper function
    def replacer(match):
        path = match.group(0)
        if any(path.lower().endswith(ext) for ext in image_exts):
            try:
                url = path_to_url(path)
                print(f"[Uploaded {path} → {url}]")
                return url
            except Exception as e:
                print(f"[Upload failed for {path}: {e}]")
                return path  # fall back to original path
        return path

    return re.sub(path_pattern, replacer, text)

async def prepare_tools():
    tools = []
    instructions = ""
    for server in MCP_SERVERS:
        if server["enabled"]:
            mcpServer = MCPTools(transport="sse", url=server["url"], timeout_seconds = 3600)
            await mcpServer.connect()
            tools.append(mcpServer)
            instructions += """\n""" + server["instruct"]

    return tools, instructions


@asynccontextmanager
async def make_agent():
    """Context manager that connects to MCP and yields a ready Agent."""

    tools, instructions = await prepare_tools()

    try:
        agent = Agent(
            model=Ollama(id="llama3-groq-tool-use"),
            tools=tools,
            instructions=instructions,
            debug_mode=True
        )
        yield agent
    finally: 
        for tool in tools:
            await tool.cleanup()

async def chat(agent: Agent, user_msg: str):
    user_msg = check_for_path(user_msg)
    async for chunk in agent.arun(user_msg, stream=True):
        if chunk.content:
            yield chunk.content


async def run_agent() -> None:
    # old code
    try:
        async with make_agent() as agent:
            print("Chat started. Type 'exit' to quit.\n")
            while True:
                user_msg = input("You: ").strip()
                if user_msg.lower() in {"exit", "quit"}:
                    break
                if not user_msg:
                    continue

                print("\nAssistant:")
                try:
                    async for chunk in chat(agent, user_msg):
                        print(chunk, end="", flush=True)
                except Exception as e:
                    print(f"\n[Agent error] {e}")
                print()

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    asyncio.run(run_agent())