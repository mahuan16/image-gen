from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.ollama import Ollama
from agno.os import AgentOS
from agno.tools.mcp import MCPTools

import os
import re
import asyncio
import requests


def path_to_url(file_path: str) -> str:

    with open(file_path, "rb") as f:
       response = requests.post(
            "https://litterbox.catbox.moe/resources/internals/api.php",  # ← full path
            data={"reqtype": "fileupload", "time": "24h"},
            files={"fileToUpload": f}
        )
    response.raise_for_status()
    return response.text.strip()



def check_for_path(text: str) -> str:
    # will check for path
    path_pattern = r'[A-Za-z]?:?[/\\][\w/\\.\-]+'
    image_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    
    # callback heloper function
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


async def run_agent() -> None:

    url = "https://postrhinal-arlinda-undelightful.ngrok-free.dev/sse"
    try:
        async with MCPTools(transport="sse", url=url, timeout_seconds=3600) as mcp_tools:
            agent = Agent(
                model=Ollama(id="llama3-groq-tool-use"),
                tools=[mcp_tools],
                instructions="""You are an image-generation assistant with access to MCP tools.

    `           Important rules:

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
                - Otherwise rely on the remembered current values

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
                - If the user asks you to check the image progress, call get_image_result""",
                debug_mode=True
            )

            print("Chat started. Type 'exit' to quit.\n")
            while True:
                user_msg = input("You: ").strip()
                if user_msg.lower() in {"exit", "quit"}:
                    break
                if not user_msg:
                    continue

                print("\nAssistant:")
                try:
                    user_msg = check_for_path(user_msg)
                    #print(user_msg)
                    await agent.aprint_response(user_msg, stream=True)
                except Exception as e:
                    print(f"\n[Agent error] {e}")
                print()

        # await agent.aprint_response("set the prompt to put the girl in a green dress and elegant pose, and generate the image", stream=True)

    except Exception as e:
        print("Error:", e)



if __name__ == "__main__":

    asyncio.run(run_agent())