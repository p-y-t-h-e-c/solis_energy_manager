# Deploying a Dagster Application with Docker

This document describes how to package and deploy a Dagster application using Docker, Docker Compose and PostgreSQL.

The architecture is designed to support both local development and production deployment while keeping the application code, Dagster infrastructure and Docker runtime concerns clearly separated.

The example application used throughout this document is `solis_energy_manager`.

---

## 1. Architecture and Deployment Model

The application uses Dagster's gRPC code-server architecture with `DockerRunLauncher`.

In production, the application runs as several Docker Compose services:

```text
                              ┌──────────────────────┐
                              │   Dagster Webserver  │
                              │        :3000         │
                              └──────────┬───────────┘
                                         │
                                   workspace.yaml
                                         │
                                        gRPC
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │    Dagster Code      │
                              │      Server          │
                              │        :4000         │
                              └──────────┬───────────┘
                                         │
                                    Repository
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │    Dagster Daemon    │
                              │                      │
                              │  DockerRunLauncher   │
                              └──────────┬───────────┘
                                         │
                                  Creates a new
                                  run container
                                         │
                                         ▼
                       ┌──────────────────────────────────┐
                       │          Run Container           │
                       │                                  │
                       │  Same application Docker image   │
                       │                                  │
                       │  dagster api execute_run ...     │
                       └───────────────┬──────────────────┘
                                       │
                         ┌─────────────┴─────────────┐
                         ▼                           ▼
                ┌─────────────────┐         ┌─────────────────┐
                │   SolisCloud    │         │    Pingram      │
                │      API        │         │      API        │
                └─────────────────┘         └─────────────────┘


                              ┌──────────────────────┐
                              │     PostgreSQL       │
                              │                      │
                              │   Dagster metadata   │
                              └──────────────────────┘
```

### 1.1 Service responsibilities

| Service                          | Responsibility                      |
| -------------------------------- | ----------------------------------- |
| `docker_postgresql_db`           | Stores Dagster metadata             |
| `solis_energy_manager_code`      | Hosts the Dagster gRPC code server  |
| `solis_energy_manager_webserver` | Provides the Dagster UI and API     |
| `solis_energy_manager_daemon`    | Manages schedules and launches runs |
| Run container                    | Executes an individual Dagster run  |

The PostgreSQL database is used for **Dagster metadata only**. The application does not use PostgreSQL to store Solis data.

### 1.2 Important distinction: services vs run containers

The Docker Compose services are long-running containers.

A Dagster run is different.

When a run starts, `DockerRunLauncher` creates a **new container from the same application image**.

It does not execute the run inside the existing daemon or code-server container, and it does not build another image.

For example:

```text
Docker image:
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest

        │
        ├── Code server container
        ├── Webserver container
        ├── Daemon container
        │
        └── Run container
            └── Executes one Dagster run
```

This provides isolation between individual runs while allowing all containers to use the same application environment.

---

## 2. Project Structure and Dependencies

The project should keep application code separate from Docker and Dagster infrastructure configuration.

A typical structure is:

```text
solis_energy_manager/
├── Dockerfile
├── docker-compose.yaml
├── docker-compose.local.yaml
├── dagster.yaml
├── workspace.yaml
├── pyproject.toml
├── uv.lock
└── src/
    └── solis_energy_manager/
        ├── __init__.py
        ├── assets.py
        ├── definitions.py
        └── settings.py
```

### 2.1 Python dependencies

Runtime dependencies must be declared in `[project.dependencies]` because the production image is built without development dependencies.

For example:

```toml
[project]
name = "solis_energy_manager"
version = "0.1.0"
requires-python = ">=3.13,<3.14"

dependencies = [
    "dagster==1.13.21",
    "dagster-docker==1.13.21",
    "dagster-postgres==0.29.21",
    "dagster-webserver==1.13.21",
    "pingram-python>=1.0.31",
    "pydantic-settings>=2.15.0",
]

[dependency-groups]
dev = [
    "dagster-dg-cli",
    "pre-commit>=4.6.2",
]
```

The development dependency group is intended only for tools required during development and CI.

---

## 3. Application Configuration

Application configuration should be handled by the application itself.

For example, `settings.py` can use Pydantic Settings:

```python
class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    solis_api_url: str = "https://www.soliscloud.com:13333"
    solis_api_base: str = "/v1/api/"
    solis_key_id: SecretStr = Field(validation_alias="SOLIS_KEY_ID")
    solis_key_secret: SecretStr = Field(validation_alias="SOLIS_KEY_SECRET")
    solis_inverter_sn: SecretStr = Field(validation_alias="SOLIS_INVERTER_SN")

    api_call_attempts: int = 5
    api_call_delay: int = 30  # seconds

    fallback_max_retry: int = 3
    fallback_retry_delay: int = 60  # seconds

    pingram_api_url: str = "https://api.eu.pingram.io"
    pingram_api_key: SecretStr = Field(validation_alias="PINGRAM_API_KEY")
    destination_email: SecretStr = Field(validation_alias="DESTINATION_EMAIL")
    from_name: str = "Solis Energy Manager"

    schedule_name: str = "daily_refresh"
    cron_schedule: str = "* 16 * * *"  # runs once every day at 4:00 PM


@cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
```

The settings object should contain only variables required by the application.

### 3.1 Application environment variables

| Variable            | Purpose                      | Sensitive |
| ------------------- | ---------------------------- | --------- |
| `SOLIS_KEY_ID`      | SolisCloud API key ID        | Yes       |
| `SOLIS_KEY_SECRET`  | SolisCloud API secret        | Yes       |
| `SOLIS_INVERTER_SN` | Solis inverter serial number | Yes       |
| `PINGRAM_API_KEY`   | Pingram API authentication   | Yes       |
| `DESTINATION_EMAIL` | Notification recipient       | Yes       |

### 3.2 Infrastructure environment variables

PostgreSQL variables are different:

| Variable            | Purpose                  |
| ------------------- | ------------------------ |
| `POSTGRES_USER`     | PostgreSQL username      |
| `POSTGRES_PASSWORD` | PostgreSQL password      |
| `POSTGRES_DB`       | PostgreSQL database name |

These are **Dagster/PostgreSQL infrastructure configuration**.

They should not be added to the application's Pydantic `Settings` class.

This separation prevents infrastructure configuration from becoming unnecessarily coupled to application code.

---

## 4. Dagster Instance Configuration

Dagster needs persistent storage for run, schedule and event-log metadata.

PostgreSQL is used for this purpose.

The Dagster instance is configured through `dagster.yaml`.

### 4.1 DockerRunLauncher

The application uses `DockerRunLauncher` so that each Dagster run executes in its own Docker container.

```yaml
run_launcher:
  module: dagster_docker
  class: DockerRunLauncher

  config:
    env_vars:
      - POSTGRES_USER
      - POSTGRES_PASSWORD
      - POSTGRES_DB

      - SOLIS_KEY_ID
      - SOLIS_KEY_SECRET
      - SOLIS_INVERTER_SN

      - PINGRAM_API_KEY
      - DESTINATION_EMAIL

    network: solis_energy_manager_network

    container_kwargs:
      volumes:
        - /var/run/docker.sock:/var/run/docker.sock
```

### Why are the PostgreSQL variables included here?

A run container is a new Dagster process.

When it starts, it needs to reconstruct the Dagster instance so that it can access the configured run storage and event log storage.

Therefore the PostgreSQL environment variables must be passed into the run container.

This does **not** mean they belong in the application's `Settings` class.

They belong in the Dagster runtime configuration.

### 4.2 Docker socket

`DockerRunLauncher` requires access to the Docker daemon so that the Dagster daemon can create run containers.

The daemon service therefore mounts:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

The run launcher configuration also passes the socket into the dynamically-created run container:

```yaml
container_kwargs:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
```

These serve different purposes:

```text
Docker host
    │
    │ /var/run/docker.sock
    ▼
Dagster daemon
    │
    │ DockerRunLauncher
    │
    ▼
Docker Engine
    │
    └── creates run container
```

### 4.3 PostgreSQL storage

The Dagster instance uses PostgreSQL for its run, schedule and event-log storage.

```yaml
run_storage:
  module: dagster_postgres.run_storage
  class: PostgresRunStorage
  config:
    postgres_db:
      hostname: docker_postgresql_db
      username:
        env: POSTGRES_USER
      password:
        env: POSTGRES_PASSWORD
      db_name:
        env: POSTGRES_DB
      port: 5432

schedule_storage:
  module: dagster_postgres.schedule_storage
  class: PostgresScheduleStorage
  config:
    postgres_db:
      hostname: docker_postgresql_db
      username:
        env: POSTGRES_USER
      password:
        env: POSTGRES_PASSWORD
      db_name:
        env: POSTGRES_DB
      port: 5432

event_log_storage:
  module: dagster_postgres.event_log
  class: PostgresEventLogStorage
  config:
    postgres_db:
      hostname: docker_postgresql_db
      username:
        env: POSTGRES_USER
      password:
        env: POSTGRES_PASSWORD
      db_name:
        env: POSTGRES_DB
      port: 5432

telemetry:
  enabled: false
```

---

## 5. Build the Docker Image

The Docker image provides the complete runtime environment used by:

* the Dagster code server;
* the Dagster webserver;
* the Dagster daemon;
* dynamically-created run containers.

### 5.1 Dockerfile

```dockerfile
FROM python:3.13.15-slim-trixie

## Install uv
COPY --from=ghcr.io/astral-sh/uv:<PINNED_VERSION> /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DAGSTER_HOME=/opt/dagster/dagster_home \
    PATH="/opt/dagster/app/.venv/bin:$PATH"

## Dagster instance configuration
RUN mkdir -p ${DAGSTER_HOME}

WORKDIR /opt/dagster/app

## Dagster configuration
COPY dagster.yaml ${DAGSTER_HOME}/dagster.yaml
COPY workspace.yaml .

## Install dependencies first so this layer can be cached
COPY pyproject.toml uv.lock ./

RUN uv sync \
    --frozen \
    --no-install-project \
    --no-dev

## Install the application
COPY src ./src

RUN uv sync \
    --frozen \
    --no-dev

EXPOSE 4000

CMD ["uv", "run", "dagster", "api", "grpc",
     "-h", "0.0.0.0",
     "-p", "4000",
     "-f", "/opt/dagster/app/src/solis_energy_manager/definitions.py"]
```

### 5.2 Python virtual environment

`uv sync` creates the project environment under:

```text
/opt/dagster/app/.venv
```

The environment's executable directory is explicitly added to `PATH`:

```dockerfile
PATH="/opt/dagster/app/.venv/bin:$PATH"
```

This is important because dynamically-created Dagster run containers are launched using the `dagster` executable.

Without the virtual environment directory in `PATH`, the container can contain Dagster correctly but still fail with:

```text
exec: "dagster": executable file not found in $PATH
```

### 5.3 Build optimisation

Dependencies are copied and installed before the application source:

```dockerfile
COPY pyproject.toml uv.lock ./

RUN uv sync \
    --frozen \
    --no-install-project \
    --no-dev

COPY src ./src

RUN uv sync \
    --frozen \
    --no-dev
```

This allows Docker to reuse the dependency layer when only application source code changes.

---

## 6. Dagster Workspace

The webserver needs to know where the gRPC code server is running.

`workspace.yaml` defines this connection:

```yaml
load_from:
  - grpc_server:
      host: solis_energy_manager_code
      port: 4000
      location_name: "solis_energy_manager"
```

The hostname is the Docker Compose service name.

The communication path is therefore:

```text
Dagster Webserver
       │
       │ gRPC :4000
       ▼
solis_energy_manager_code
       │
       ▼
definitions.py
```

Port `4000` does not need to be exposed on the host because the webserver and code server communicate over the Docker network.

---

## 7. Docker Compose

Docker Compose brings the infrastructure and Dagster services together.

### 7.1 PostgreSQL

```yaml
services:

  docker_postgresql_db:
    image: postgres:16
    container_name: docker_postgresql_db
    restart: unless-stopped

    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}

    volumes:
      - dagster_postgres_data:/var/lib/postgresql/data

    networks:
      - solis_energy_manager_network

    healthcheck:
      test:
        - CMD-SHELL
        - pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
```

PostgreSQL is not published to the host.

It is accessible to other services through the internal Docker network on port `5432`.

### 7.2 Dagster code server

```yaml
  solis_energy_manager_code:
    image: ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
    container_name: solis_energy_manager_code
    restart: unless-stopped

    environment:
      DAGSTER_CURRENT_IMAGE: "ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest"

      SOLIS_KEY_ID: ${SOLIS_KEY_ID}
      SOLIS_KEY_SECRET: ${SOLIS_KEY_SECRET}
      SOLIS_INVERTER_SN: ${SOLIS_INVERTER_SN}

      PINGRAM_API_KEY: ${PINGRAM_API_KEY}
      DESTINATION_EMAIL: ${DESTINATION_EMAIL}

    healthcheck:
      test:
        - CMD
        - python
        - -c
        - |
          import socket
          s = socket.socket()
          s.settimeout(2)
          s.connect(("127.0.0.1", 4000))
          s.close()
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s

    networks:
      - solis_energy_manager_network

    depends_on:
      docker_postgresql_db:
        condition: service_healthy
```

The code server provides the gRPC interface used by the Dagster webserver and daemon.

### 7.3 Dagster webserver

```yaml
  solis_energy_manager_webserver:
    image: ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
    container_name: solis_energy_manager_webserver
    restart: unless-stopped

    command:
      - /opt/dagster/app/.venv/bin/dagster-webserver
      - -h
      - 0.0.0.0
      - -p
      - "3000"
      - -w
      - /opt/dagster/app/workspace.yaml

    ports:
      - "3000:3000"

    environment:
      DAGSTER_CURRENT_IMAGE: "ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest"

      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}

      SOLIS_KEY_ID: ${SOLIS_KEY_ID}
      SOLIS_KEY_SECRET: ${SOLIS_KEY_SECRET}
      SOLIS_INVERTER_SN: ${SOLIS_INVERTER_SN}

      PINGRAM_API_KEY: ${PINGRAM_API_KEY}
      DESTINATION_EMAIL: ${DESTINATION_EMAIL}

    networks:
      - solis_energy_manager_network

    depends_on:
      docker_postgresql_db:
        condition: service_healthy
      solis_energy_manager_code:
        condition: service_healthy
```

Only the webserver needs to be published to the host:

```yaml
ports:
  - "3000:3000"
```

### 7.4 Dagster daemon

```yaml
  solis_energy_manager_daemon:
    image: ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
    container_name: solis_energy_manager_daemon
    restart: unless-stopped

    command:
      - /opt/dagster/app/.venv/bin/dagster-daemon
      - run

    environment:
      DAGSTER_CURRENT_IMAGE: "ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest"

      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}

      SOLIS_KEY_ID: ${SOLIS_KEY_ID}
      SOLIS_KEY_SECRET: ${SOLIS_KEY_SECRET}
      SOLIS_INVERTER_SN: ${SOLIS_INVERTER_SN}

      PINGRAM_API_KEY: ${PINGRAM_API_KEY}
      DESTINATION_EMAIL: ${DESTINATION_EMAIL}

    volumes:
      - /var/run/docker.sock:/var/run/docker.sock

    networks:
      - solis_energy_manager_network

    depends_on:
      docker_postgresql_db:
        condition: service_healthy
      solis_energy_manager_code:
        condition: service_healthy
```

The daemon is responsible for detecting scheduled runs and asking `DockerRunLauncher` to create the corresponding run containers.

---

## 8. Docker Networks and Volumes

The services communicate using a dedicated Docker network:

```yaml
networks:
  solis_energy_manager_network:
    driver: bridge
    name: solis_energy_manager_network
```

A named volume provides persistent PostgreSQL storage:

```yaml
volumes:
  dagster_postgres_data:
    name: solis_energy_manager_postgres_data
```

The complete Compose configuration therefore ends with:

```yaml
networks:
  solis_energy_manager_network:
    driver: bridge
    name: solis_energy_manager_network

volumes:
  dagster_postgres_data:
    name: solis_energy_manager_postgres_data
```

---

## 9. Service Startup Order

There are dependencies between the services:

```text
PostgreSQL
    │
    ├── healthcheck passes
    │
    ▼
Code server
    │
    ├── healthcheck passes
    │
    ├──────────────┐
    ▼              ▼
Webserver        Daemon
```

The `healthcheck` and `depends_on: condition: service_healthy` configuration is important.

Simply starting a container does not mean the service inside it is ready to accept connections.

Without the healthcheck, the webserver can start before the gRPC code server is ready and produce connection errors during startup.

---

## 10. Local Development

Production Compose uses the published Docker image:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

For local development, a Compose override builds the image locally instead.

`docker-compose.local.yaml`:

```yaml
services:

  solis_energy_manager_code:
    build:
      context: .
      dockerfile: Dockerfile
    image: solis_energy_manager:local

    environment:
      DAGSTER_CURRENT_IMAGE: "solis_energy_manager:local"

  solis_energy_manager_webserver:
    build:
      context: .
      dockerfile: Dockerfile
    image: solis_energy_manager:local

    environment:
      DAGSTER_CURRENT_IMAGE: "solis_energy_manager:local"

  solis_energy_manager_daemon:
    build:
      context: .
      dockerfile: Dockerfile
    image: solis_energy_manager:local

    environment:
      DAGSTER_CURRENT_IMAGE: "solis_energy_manager:local"
```

### 10.1 Why `DAGSTER_CURRENT_IMAGE` must change locally

`DockerRunLauncher` needs to know which image to use when creating a run container.

Production:

```text
DAGSTER_CURRENT_IMAGE=
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

Local development:

```text
DAGSTER_CURRENT_IMAGE=
solis_energy_manager:local
```

If the local override changes the service image but does not change `DAGSTER_CURRENT_IMAGE`, the daemon will attempt to create the run container using the production image.

This can result in errors such as:

```text
No such image: ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

or an attempted Docker Hub pull.

### 10.2 Starting the local environment

```bash
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.local.yaml \
  up --build
```

For a clean rebuild:

```bash
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.local.yaml \
  down

docker compose \
  -f docker-compose.yaml \
  -f docker-compose.local.yaml \
  build --no-cache

docker compose \
  -f docker-compose.yaml \
  -f docker-compose.local.yaml \
  up
```

The Dagster UI is then available on port `3000`.

---

## 11. Production Deployment

The production deployment uses GitHub Actions to build the application Docker image, publish it to the GitHub Container Registry (GHCR), and update the application running on the Oracle VM.

The deployment architecture is:

```text
                         GitHub

                           │

                           ▼

                    GitHub Actions

                           │

                    Build Docker image

                           │

                           ▼

                         GHCR
                  GitHub Container Registry

                           │

                    authenticated pull

                           │

                           ▼

                     Oracle VM

                           │

                    Docker Compose

                           │

             ┌─────────────┼─────────────┐

             ▼             ▼             ▼

          Dagster       Dagster       Dagster

           Code        Webserver       Daemon
```

The container image is associated with the GitHub repository and is stored as a private package in GHCR.

The GitHub Actions workflow is responsible for:

1. Building the Docker image.
2. Publishing the image to GHCR.
3. Tagging the image with `latest` and the Git commit SHA.
4. Preparing the production environment configuration.
5. Copying the deployment configuration to the Oracle VM.
6. Updating the running Docker Compose application.

The detailed GitHub Actions implementation is documented separately.

---

## 12. Environment and Secrets in Production

The production deployment uses a `.env` file for Docker Compose variable substitution.

For example:

```text
POSTGRES_USER=dagster
POSTGRES_PASSWORD=<secret>
POSTGRES_DB=dagster

SOLIS_KEY_ID=<secret>
SOLIS_KEY_SECRET=<secret>
SOLIS_INVERTER_SN=<serial>

PINGRAM_API_KEY=<secret>
DESTINATION_EMAIL=<email>
```

Sensitive values should be stored as GitHub Actions secrets rather than committed to the repository.

At minimum, the following should be treated as secrets:

```text
POSTGRES_PASSWORD
SOLIS_KEY_ID
SOLIS_KEY_SECRET
PINGRAM_API_KEY
```

`POSTGRES_USER` and `POSTGRES_DB` are configuration values rather than credentials, although they should still not be committed if the deployment convention is to keep all environment-specific configuration outside the repository.

For a small personal deployment, storing `.env` on the VM with appropriate file permissions is reasonable.

A future improvement would be to generate the `.env` file directly on the VM rather than creating and transferring it from the GitHub Actions runner.

---

## 13. GitHub Actions Deployment

GitHub Actions provides the automated CI/CD pipeline used to build and deploy the application.

The workflow is triggered when changes are pushed to the `main` branch.

At a high level, the workflow consists of two stages:

```text
GitHub push to main
        │
        ▼
┌───────────────────────────────┐
│ Build and publish Docker image│
│                               │
│ GitHub Actions                │
│        │                      │
│        ▼                      │
│ GHCR                          │
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│ Deploy to Oracle VM           │
│                               │
│ Copy deployment configuration │
│        │                      │
│        ▼                      │
│ Docker Compose                │
│        │                      │
│        ▼                      │
│ Pull new image                │
│        │                      │
│        ▼                      │
│ Restart application           │
└───────────────────────────────┘
```

The Docker image is published to the GitHub Container Registry using the GitHub Actions workflow token.

The image is tagged using both:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest

ghcr.io/p-y-t-h-e-c/solis_energy_manager:<commit-sha>
```

The `latest` tag provides the normal deployment reference, while the commit SHA provides an immutable reference to a specific version of the application.

The Oracle VM authenticates to GHCR separately in order to pull the private container image.

Production application secrets are supplied to the deployment environment and are not included in the Docker image.

The detailed workflow configuration, GitHub permissions, GHCR authentication, deployment secrets and SSH deployment process are documented in the separate **GitHub Actions Deployment** document.

---

## 14. Runtime Execution

Once the infrastructure is running, a normal Dagster run follows this sequence:

```text
1. User or schedule starts a Dagster run
             │
             ▼
2. Dagster Webserver creates the run
             │
             ▼
3. Run enters the queue
             │
             ▼
4. Dagster Daemon detects the queued run
             │
             ▼
5. DockerRunLauncher reads DAGSTER_CURRENT_IMAGE
             │
             ▼
6. Docker creates a new run container
             │
             ▼
7. Container executes:
       dagster api execute_run ...
             │
             ▼
8. Run container reconstructs the Dagster instance
             │
             ▼
9. Dagster connects to PostgreSQL
             │
             ▼
10. Repository and assets are loaded
             │
             ▼
11. Application calls SolisCloud
             │
             ▼
12. Application performs its processing
             │
             ▼
13. Pingram sends the notification
             │
             ▼
14. Run completes
             │
             ▼
15. Run container exits
```

The run container exiting after the run is therefore expected behaviour.

It is not a failed service container simply because it is no longer running.

---

## 15. PostgreSQL Persistence

PostgreSQL stores Dagster metadata in a named Docker volume:

```yaml
volumes:
  dagster_postgres_data:
    name: solis_energy_manager_postgres_data
```

The database container itself can therefore be recreated without losing Dagster metadata.

The persistent data is stored in:

```text
solis_energy_manager_postgres_data
```

rather than inside the PostgreSQL container.

### 15.1 PostgreSQL initialisation behaviour

The `POSTGRES_*` environment variables are primarily used when PostgreSQL initialises a new database directory.

Changing them after the named volume already exists does **not** recreate the database or automatically create a new PostgreSQL role.

For example:

```text
Existing PostgreSQL volume
        │
        │ Change POSTGRES_USER
        ▼
Existing database remains unchanged
```

This can produce errors such as:

```text
FATAL: role "solis_energy_manager" does not exist
```

when the new username has not been created in the existing database.

If the Dagster metadata can safely be discarded, the database can be reinitialised by removing the volume.

If the metadata must be retained, the new PostgreSQL role should instead be created and granted the appropriate permissions.

**Do not remove the volume if preserving Dagster history is important.**

---

## 16. Deployment Verification

After deploying, verify the Compose services:

```bash
docker compose ps
```

The expected long-running services are:

```text
docker_postgresql_db
solis_energy_manager_code
solis_energy_manager_webserver
solis_energy_manager_daemon
```

Check individual logs when required:

```bash
docker logs solis_energy_manager_code
docker logs solis_energy_manager_webserver
docker logs solis_energy_manager_daemon
```

The application image can also be checked:

```bash
docker images
```

---

## 17. End-to-End Run Verification

A deployment should not be considered complete until an actual Dagster run has been successfully executed.

The verification sequence should be:

```text
Docker Compose
      │
      ▼
All services healthy
      │
      ▼
Dagster UI accessible
      │
      ▼
Repository loaded
      │
      ▼
Job/asset visible
      │
      ▼
Manual run started
      │
      ▼
Daemon detects run
      │
      ▼
Run container created
      │
      ▼
Run container starts successfully
      │
      ▼
PostgreSQL connection succeeds
      │
      ▼
Application executes
      │
      ▼
External APIs respond
      │
      ▼
Run succeeds
```

This is more useful than verifying only that the four Compose services are running, because the actual workload executes in a separate dynamically-created container.

---

## 18. Troubleshooting

Troubleshooting should begin by identifying **which layer has failed**.

### 18.1 Compose services

Check:

```bash
docker compose ps
```

Then inspect logs:

```bash
docker logs <container>
```

---

### 18.2 Code server cannot be reached

Check the code-server container:

```bash
docker logs solis_energy_manager_code
```

The code server should be listening on:

```text
0.0.0.0:4000
```

Also verify its healthcheck.

If the webserver starts before the code server is ready, confirm that `depends_on` is using:

```yaml
condition: service_healthy
```

---

### 18.3 Run container is created with the wrong image

Check:

```text
DAGSTER_CURRENT_IMAGE
```

Production should use:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

Local development should use:

```text
solis_energy_manager:local
```

The daemon must use the same value as the image that was actually built or pulled.

---

### 18.4 `dagster` executable cannot be found

If the run container reports:

```text
exec: "dagster": executable file not found in $PATH
```

verify that the Dockerfile contains:

```dockerfile
PATH="/opt/dagster/app/.venv/bin:$PATH"
```

and that Dagster exists in:

```text
/opt/dagster/app/.venv/bin/dagster
```

---

### 18.5 Run container cannot connect to PostgreSQL

If a run fails with errors indicating that:

```text
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
```

are not set, check the `DockerRunLauncher` configuration.

The variables must be included in:

```yaml
run_launcher:
  ...
  config:
    env_vars:
```

They should **not** be added to the application `Settings` class merely to resolve this problem.

---

### 18.6 Run containers exit immediately

List recently-created run containers:

```bash
docker ps -a --filter ancestor=solis_energy_manager:local
```

or, in production:

```bash
docker ps -a --filter ancestor=ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

Then inspect the relevant container:

```bash
docker logs <container_id>
```

A run container exiting after a successful run is normal.

An exit code of `1` requires inspection of its logs.

---

### 18.7 PostgreSQL role does not exist

If PostgreSQL reports:

```text
FATAL: role "..." does not exist
```

check whether the named PostgreSQL volume was created before the current `POSTGRES_USER` value was configured.

Inspect the volumes:

```bash
docker volume ls
```

The application uses:

```text
solis_energy_manager_postgres_data
```

If preserving the database, do not remove the volume.

---

### 18.8 Docker cannot create the run container

Check that the daemon has access to the Docker socket:

```bash
ls -l /var/run/docker.sock
```

Also verify that the daemon is attached to:

```text
solis_energy_manager_network
```

and that `DockerRunLauncher` uses the same network.

---

### 18.9 SolisCloud returns 502/503/504

The SolisCloud API can occasionally return transient gateway errors.

The application should retry transient HTTP errors such as:

```text
502
503
504
```

Each retry should generate a new request timestamp and therefore a new request signature.

A retry sequence should use increasing delays, for example:

```text
Attempt 1
   │
   └── 502
        │
        ▼
      wait
        │
        ▼
Attempt 2
   │
   └── 502
        │
        ▼
      wait longer
        │
        ▼
Attempt 3
```

Retries should not reuse an expired request signature.

---

## 19. Configuration Reference

The following table summarises the important runtime configuration.

| Component                  | Configuration                                     |
| -------------------------- | ------------------------------------------------- |
| Application image          | `ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest` |
| Local image                | `solis_energy_manager:local`                      |
| Code server                | `:4000`                                           |
| Webserver                  | `:3000`                                           |
| PostgreSQL                 | `:5432` internally                                |
| Dagster home               | `/opt/dagster/dagster_home`                       |
| Python virtual environment | `/opt/dagster/app/.venv`                          |
| Docker network             | `solis_energy_manager_network`                    |
| PostgreSQL volume          | `solis_energy_manager_postgres_data`              |
| Run launcher               | `DockerRunLauncher`                               |
| Run container image        | `DAGSTER_CURRENT_IMAGE`                           |
| Docker socket              | `/var/run/docker.sock`                            |
| Dagster metadata           | PostgreSQL                                        |

---

## 20. Key Design Rules

The deployment follows a small number of important rules.

### Application configuration

Application secrets and settings belong in the application's environment and Pydantic configuration.

```text
SOLIS_*
PINGRAM_*
DESTINATION_EMAIL
```

### Dagster configuration

Dagster infrastructure configuration belongs in `dagster.yaml`.

```text
POSTGRES_*
DockerRunLauncher
PostgreSQL storage
Docker network
```

### Docker configuration

Docker is responsible for:

```text
Images
Containers
Networks
Volumes
Docker socket
```

### Local vs production

The same application image architecture is used in both environments.

Only the image source changes:

```text
Local:
solis_energy_manager:local

Production:
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

`DAGSTER_CURRENT_IMAGE` must always match the image available to the Docker daemon.

### Run execution

A Dagster run is executed in a new container created from the application image.

```text
Docker Compose service
        ≠
Dagster run container
```

The run container is intentionally ephemeral.

### PostgreSQL

PostgreSQL stores Dagster metadata and uses a persistent Docker volume.

```text
PostgreSQL container
        +
persistent volume
        =
persistent Dagster metadata
```

### Runtime dependencies

All packages required by the production application must be in:

```toml
[project.dependencies]
```

Development-only tooling belongs in:

```toml
[dependency-groups]
dev = [...]
```

### Python executable

The project virtual environment must be available on `PATH`:

```text
/opt/dagster/app/.venv/bin
```

This allows dynamically-created run containers to execute the `dagster` command correctly.

---

## 21. Final Deployment Flow

Once configured, the complete system can be understood as a simple sequence:

```text
                         DEVELOPMENT

                              │

                              ▼

                    Write application code

                              │

                              ▼

                     Update dependencies

                              │

                              ▼

                       Test locally

                              │

                              ▼

                        Push to main

                              │

                              ▼

                       GITHUB ACTIONS

                              │

                    Build Docker image

                              │

                              ▼

                             GHCR

                    GitHub Container Registry

                              │

                              ▼

                           Oracle VM

                              │

                              ▼

                     Docker Compose pull

                              │

                              ▼

                     Docker Compose up

                              │

                              ▼

                     ┌─────────────────┐
                     │ Dagster stack   │
                     │                 │
                     │ PostgreSQL      │
                     │ Code server     │
                     │ Webserver       │
                     │ Daemon          │
                     └────────┬────────┘
                              │
                         scheduled run
                              │
                              ▼
                     DockerRunLauncher
                              │
                              ▼
                     Ephemeral run
                       container
                              │
                              ▼
                       Run application
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
                SolisCloud           Pingram
```

This architecture keeps the responsibilities of the application, Dagster, Docker and CI/CD infrastructure separate.

GitHub Actions handles the automated build and deployment process, GHCR provides private container image storage, Docker Compose manages the production services, and Dagster manages the execution of individual application runs.

---
