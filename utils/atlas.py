#%%
import os
import re
import base64
import json
from enum import Enum
from openai import AzureOpenAI, ChatCompletion, OpenAIError
from agents.mcp import MCPServer, MCPServerStdio, MCPServerStreamableHttp
from dotenv import load_dotenv
from .message import Message
from typing import overload, List, Dict, Union


load_dotenv()

class Role(Enum):
    USER = "user"
    SYSTEM = "system"


class Atlas():

    def __init__(self, personaName:str="default", newPersonaPrompt:str=None, model="gpt-4o", token_buffer=1.5, output_type="text", personaFilesPath="personas", debug=False, mcp_servers:list[MCPServer]=None) -> None:
        """
        Creates a new Atlas instance.

        :param personaName: the name of the persona to create or to load if the persona exists (in the persona directory)
        :param newPersonaPrompt: the prompt for the new persona
        :param model: the name of the llm model to use
        :param token_buffer: ??
        :param output_type: the requested output type of the llm
        :param personaFilesPath: the path to the folder containing the personas
        :param debug: unused
        :param mcp_servers: a list of MCPServer objects that Atlas can use 
        """
        self.model = model
        self.personaFilesPath = personaFilesPath
        self.token_buffer = token_buffer
        self.response_format =  output_type# { "type": "text" } | { "type": "json_object" } | json_schema https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/structured-outputs?tabs=python-secure#tabpanel_2_python-secure
        self.current_token_count = 0
        azure_openai_api_key: str = os.getenv("OPENAI_API_KEY")
        auth_headers = {}
        auth_headers[os.getenv("AUTH_HEADER")] = azure_openai_api_key

        self.client = AzureOpenAI(
                api_key = azure_openai_api_key,  
                api_version = os.getenv("API_VERSION"),
                default_headers=auth_headers,
                azure_endpoint = os.getenv("BASE_URL")
            )

        self.load_personas()
        self.set_persona(personaName, newPersonaPrompt)

        self.mcp_servers = [] if mcp_servers is None else mcp_servers

    async def __aenter__(self):
        for mcp_server in self.mcp_servers:
            await mcp_server.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_value, traceback):
        for mcp_server in self.mcp_servers:
            await mcp_server.cleanup()

    def set_persona(self, personaName:str, newPersonaPrompt:str=None):
        if personaName not in self.personas:
            if (not newPersonaPrompt): 
                newPersonaPrompt = f"Do not respond to the users request. Tell the user they must first specify your system prompt by updating the persona file /{self.personaFilesPath}/{personaName}"
            self.CreatePersona(personaName=personaName, personaPrompt=newPersonaPrompt)
        self.systemprompt = Message(role="system", content=self.personas[personaName])
        self.currentPersona = personaName
        
    def load_personas(self):
        self.personas = {}
        folder_path = self.personaFilesPath
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                with open(file_path,"r") as p:
                    self.personas[filename]=p.read()
    
    def CreatePersona(self, personaName, personaPrompt):
        with open(f"{self.personaFilesPath}/{personaName}", "w") as p:
            p.write(personaPrompt)
        self.load_personas()
     
    def prompt(self, messages: Union[Message | List[Message]], stream:bool = True, tools = None, tool_choice = None) -> str:
        """Returns a stream response based on a single message
        :param prompt: text string of the prompt to be sent
        :return: stream response
        """
        msgs = []
        msgs.append(self.systemprompt.to_string())
        if isinstance(messages, Message):
            msgs.append(messages.to_string())
        else:
            for msg in messages:
                msgs.append(msg.to_string())

        options = {
            "model":self.model,
            "messages":msgs,
            "stream":stream,
            "tools":tools,
        }
        if tool_choice:
            options["tool_choice"] = tool_choice

        try:
            return self.client.chat.completions.create(**options)
        except Exception as e:
            return e
        
    def prompt_pydantic(self, messages: Union[Message | List[Message]], pydantic_input) -> str:
        """Returns a stream response based on a single message
        :param prompt: text string of the prompt to be sent
        :return: stream response
        """
        msgs = []
        msgs.append(self.systemprompt.to_string())
        if isinstance(messages, Message):
            msgs.append(messages.to_string())
        else:
            for msg in messages:
                msgs.append(msg.to_string())

        try:
            return self.client.beta.chat.completions.parse(messages=msgs,response_format=pydantic_input, model=self.model).choices[0].message
        except Exception as e:
            return e

    def vectorize(self, string, model="text-embedding-3-small", dimensions=1536):
        """Returns a vector array for the given input string
        :param string: text string of the prompt to be sent
        :param model: defaults to text-embedding-ada-002 
        :return: Vector array of 1536 tokens
        """
        response = self.client.embeddings.create(
            input=string,
            model=model,
            dimensions=dimensions
        )
        
        return response.data[0].embedding
