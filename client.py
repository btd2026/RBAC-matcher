"""
RBAC-matcher Client

A command-line Python client for communicating with the RBAC-matcher Multi-MCP server, and
invoking agent-driven natural language commands (backed by OpenAI/Azure OpenAI).

Main Features:
- Loads a persona prompt for the agent from `personas/default`.
- Connects to server on user-specified port (default MCP server on 3000).
- Sends user prompts to the server and displays formatted results.
- Uses .env for configuration (see .env.example).

Prerequisites/Setup:
- Ensure environment variables (API keys, endpoints, etc.) are set in a `.env` file.
- Requires access to OpenAI/Azure OpenAI.
- See README for detailed Python environment and dependency setup.

Usage:
- Run the script (see README for uv invocation).
- Specify server port to connect.
- Type NL queries or commands; type 'exit' to quit.

See README or inline error output for troubleshooting help.
"""

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
from openai import OpenAIError, AsyncAzureOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from agents.run_context import RunContextWrapper

dotenv.load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("BASE_URL")
api_version = os.getenv("API_VERSION")
model_standard = os.getenv("MODEL")

auth_headers = {}
api_key = os.getenv("OPENAI_API_KEY")
auth_header_key = os.getenv("AUTH_HEADER")
if auth_header_key:
    auth_headers[auth_header_key] = api_key

# Disable tracing since we're using Azure OpenAI
set_tracing_disabled(disabled=True)

async def run(mcp_servers: list):
    try:
        # Load persona instructions from personas/default
        with open("personas/default", "r") as f:
            persona_instructions = f.read()

        # Create the Asychronous AzureOpenAI client to connect to Atlas API
        client = AsyncAzureOpenAI(
            api_key=openai_api_key,
            api_version=api_version,
                default_headers=auth_headers,
            azure_endpoint=base_url
            )

        # Configure the agent with AzureOpenAI as the backend
        agent = Agent(
            name="Assistant",
            instructions=f"{persona_instructions}\n\nToday's date is: {time.ctime()}",
            model=OpenAIChatCompletionsModel(
                model=model_standard,
                openai_client=client,
            ),
            mcp_servers=mcp_servers,
        )

        while True:
            prompt = input("> ")
            if prompt.lower() == "exit":
                quit()
            result = await Runner.run(agent, prompt)
            print(result.final_output)

    except OpenAIError as e:
        print(f"OpenAI API Error: {str(e)}")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")

async def main():
    port_input = input("port: ")
    try:
        port = int(port_input)
    except ValueError:
        print("Invalid port number.")
        return
    async with (agents.mcp.MCPServerStreamableHttp(
        params={
            "url": f"http://localhost:{port}/mcp/"
        }, client_session_timeout_seconds=30
    )) as server:
        await run([server])

if __name__ == "__main__":
    asyncio.run(main())

