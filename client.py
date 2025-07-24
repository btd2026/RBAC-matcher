import os
import dotenv
from dataclasses import dataclass
from typing import Literal
import asyncio
import time

import agents.mcp
import agents
from openai import BaseModel
import openai
from openai import OpenAIError
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from agents.run_context import RunContextWrapper

dotenv.load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("Base_URL")
api_version = os.getenv("API_Version")
model_standard = os.getenv("Model")

auth_headers = {}
api_key = os.getenv("OPENAI_API_KEY")
auth_headers[os.getenv("AUTH_HEADER")] = api_key

# Disable tracing since we're using Azure OpenAI
set_tracing_disabled(disabled=True)

async def run(mcp_servers: list):
    try:
        # Create the OpenAI client
        # The agents OpenAIChatCompletionsModel expects a client, so we pass openai itself
        client = openai

        # Configure the agent with OpenAI
        agent = Agent(
            name="Assistant",
            instructions=f"You are a helpful assistant. Today's date is: {time.ctime()}",
            model=OpenAIChatCompletionsModel(
                model=model_standard,
                openai_client=client,
            ),
            mcp_servers=mcp_servers
        )
        while True:
            prompt = input("> ")
            if prompt == "exit":
                quit()
            result = await Runner.run(agent, prompt)
            print(result.final_output)

    except OpenAIError as e:
        print(f"OpenAI API Error: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

async def main():
    port = int(input("port: "))
    async with (agents.mcp.MCPServerStreamableHttp(
        params={
            "url": f"http://localhost:{port}/mcp/"
        }, client_session_timeout_seconds=30
    )) as server:
        await run([server])

if __name__ == "__main__":
    asyncio.run(main())
