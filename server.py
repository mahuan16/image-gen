from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent import make_agent, chat, MCP_SERVERS, prepare_tools
from agno.agent import Agent
from agno.models.ollama import Ollama
import agent as agent_module

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with make_agent() as agent:
        app.state.agent = agent
        yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat_endpoint(req: ChatRequest, request: Request):
    agent = request.app.state.agent

    async def token_generator():
        try:
            async for chunk in chat(agent, req.message):
                yield chunk
        except Exception as e:
            yield f"\n\n[Error: {e}]"

    return StreamingResponse(
        token_generator(),
        media_type="text/plain; charset=utf-8",
        headers={
            "X-Accel-Buffering": "no", # load chunks imediately
            "Cache-Control": "no-cache",
        },
    )

@app.get("/servers")
async def get_servers():
    return [
        {"name":s["name"], "url": s["url"], "enabled": s["enabled"]}
        for s in MCP_SERVERS
    ]

@app.post("/servers/toggle")
async def toggle_servers(changes: dict[int, bool], request: Request):
    for idx_str, enabled in changes.items():
        idx = int(idx_str)
        if 0 <= idx < len(agent_module.MCP_SERVERS):
            agent_module.MCP_SERVERS[idx]["enabled"] = enabled

    # tear down old tools
    old_agent = request.app.state.agent
    for tool in old_agent.tools or []:
        try:
            await tool.cleanup()
        except Exception:
            pass

    # rebuild with new server list
    tools, instructions = await prepare_tools()
    request.app.state.agent = Agent(
        model=Ollama(id="llama3-groq-tool-use"),
        tools=tools,
        instructions=instructions,
        debug_mode=True
    )

    return {"status": "ok"}


class AddServerRequest(BaseModel):
    name: str
    url: str
    instruct: str = ""

@app.post("/servers/add")
async def add_server(req: AddServerRequest):
    agent_module.MCP_SERVERS.append({
        "name": req.name,
        "url": req.url,
        "enabled": True,
        "instruct": req.instruct,
    })
    return {"status": "ok"}

class RemoveServerRequest(BaseModel):
    index: int

@app.post("/servers/remove")
async def remove_server(req: RemoveServerRequest):
    if 0 <= req.index < len(agent_module.MCP_SERVERS):
        agent_module.MCP_SERVERS.pop(req.index)
    return {"status": "ok"}

@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=False)

    #http://localhost:8001/static/index.html