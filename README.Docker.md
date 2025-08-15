# RBAC-matcher Docker Runbook

## Building and Running RBAC-matcher
Open Docker Desktop Engine on your computer

When you're ready to run the RBAC-matcher server in Docker, use the following:

```bash
docker compose up --build
```

- This command will build the image if necessary and launch the server.
- By default, your application will be available at [http://localhost:3000](http://localhost:3000).

---

## Data & Output Directories

- Excel and CSV files for org charts must be placed in the `./data` directory (mounted into the container as `/data`).
- Generated org chart HTML files will be available in the `./output` directory (mounted as `/app/output`).
- Persona files are mounted for agent configuration via:
  - `./personas` → `/app/utils/personas`
  - `./utils`     → `/app/utils`
  
- This is set up in compose.yaml

---

## Useful Docker Commands

### Rebuilding and Restarting the Application

If you update your tools or code, rebuild the image and restart the container:

```bash
docker stop mcp-container
docker rm mcp-container
docker build -t rbac-matcher-app:latest .
docker run -d -p 3000:3000 --name mcp-container rbac-matcher-app:latest
```

Or, using Docker Compose (preferred):

```bash
docker compose build server
docker compose up -d server
```

---

### Monitoring & Maintenance

- **Tail logs:**  
  ```bash
  docker compose logs -f server
  ```

- **Verify your data and output mounts:**  
  ```bash
  docker compose exec server bash -lc 'ls -la /data && echo && ls -la /app/output'
  ```

- **Tear down all containers and volumes:**  
  ```bash
  docker compose down
  ```

---

## Cloud Deployment

To deploy on a cloud VM or server:

1. **Build your Docker image for the appropriate platform** (e.g., if deploying to amd64 from an M1 Mac):
    ```bash
    docker build --platform=linux/amd64 -t rbac-matcher-app:latest .
    ```

2. **Push your image to a container registry** (if needed):
    ```bash
    docker tag rbac-matcher-app:latest myregistry.com/rbac-matcher-app
    docker push myregistry.com/rbac-matcher-app
    ```

3. **Run your image on your server using the appropriate run or compose command.**

---

## Troubleshooting

- If files do not appear, confirm they are placed in `./data` (host) and are visible with the mount verification command above.
- HTML outputs will not auto-open in your desktop browser when running in Docker. Instead, open the generated HTML from `./output` on your host machine.
- For agent/persona changes, ensure you remount or rebuild containers as needed.

---

## References

- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Docker's Python Guide](https://docs.docker.com/language/python/)

---