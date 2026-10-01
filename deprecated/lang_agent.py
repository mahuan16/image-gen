from langchain_ollama import ChatOllama
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver

import asyncio

model = ChatOllama(model="llama3-groq-tool-use")

async def chat():
    
    client = MultiServerMCPClient(
        {
            "runninghub": {
                "transport": "sse",
                "url": "https://postrhinal-arlinda-undelightful.ngrok-free.dev/sse",
            }
        }
    )

    tools = await client.get_tools()
    #print("Loaded tools:", [t.name for t in tools])

    model_with_tools = model.bind_tools(tools)


    agent = create_agent(
        model=model_with_tools,
        tools=tools,
        system_prompt="""You are aiding the user in image editting through runninghub. 
                        use the tools to adjust the images and prompt 
                        before finally generating the image, 
                        checking on it periodically, and returning the image 
                        or any errors to the user when done.
                        
                        state the tools you are using, and call them. return the task id
                        of the image you are generating.""",
    )
    
    print("Chat started. Type 'exit' to quit.\n")
    while True:
        user_msg = input("You: ").strip()
        if user_msg.lower() in {"exit", "quit"}:
            break
        if not user_msg:
            continue
        
        result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": user_msg}]}
            )

        print("Assistant:", result["messages"][-1].content)

    

if __name__ == "__main__":
    asyncio.run(chat())