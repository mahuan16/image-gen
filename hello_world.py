
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

mcp = FastMCP("Hello World")

@mcp.tool(name="say_hello", description="says hello to specified name (given as parameter)")
def say_hello(name:str):
    return "using mcp tool! hello " + name

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(mcp.sse_app(), host="0.0.0.0", port=8002)

    #http://0.0.0.0:8002
    