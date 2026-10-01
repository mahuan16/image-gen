import asyncio
from agents import Agent, Runner

agent = Agent(
    name="Test Agent",
    instructions="You answer briefly and clearly."
)

async def main():
    result = await Runner.run(agent, "Say hello in one sentence.")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())