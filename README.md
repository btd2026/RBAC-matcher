# MCP Proof of Concept

## Prerequisites
- UV
- Docker

### Installing UV

UV is a package/project manager for python. It's great.

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Installing Docker

https://docs.docker.com/desktop/setup/install/windows-install/

## Setting up Server

First, change the `sec_edgar_user_agent` on line 19.

Next, change copy the `.env.example` to `.env` and fill out the fields (both API keys should be the same)

Run these commands:
1. `uv sync`
2. `docker build -t mcp_docker_test .`
3. `docker container create --name mcp_container -p 3000:3000 mcp_docker_test` 
4. `docker container start mcp_container`

If you open the Docker Desktop App, you should see the container running. 

## Running client

1. `uv run client.py`
2. Then enter the port you specified
3. When you see the `>` prompt, you should be all set to prompt!
4. To exit without issue, just type `exit`
