# GitHub Actions Deployment

GitHub Actions is used to automate the build, publication and deployment of the `solis_energy_manager` application.

The workflow runs when changes are pushed to the `main` branch and performs two main stages:

1. Build and publish the Docker image to the **GitHub Container Registry (GHCR)**.
2. Deploy the published image to the Oracle VM using Docker Compose.

The workflow removes the need to manually build, push and deploy a new application version after every change.

---

## 1. Deployment Flow

The complete GitHub Actions process can be summarised as:

```text
Developer
    │
    │ git push
    ▼
 GitHub
    │
    ▼
GitHub Actions
    │
    ├───────────────────────────────┐
    │                               │
    ▼                               │
Build Docker image                  │
    │                               │
    ▼                               │
Publish to GHCR                     │
    │                               │
    └───────────────┐               │
                    │               │
                    ▼               │
              Deploy to VM          │
                    │               │
                    ▼               │
             Docker Compose         │
                    │               │
                    ▼               │
              Pull new image        │
                    │               │
                    ▼               │
             Start application      │
                    │
                    ▼
              Dagster stack
```

The workflow therefore acts as the connection between the source repository and the production environment.

---

## 2. Workflow Configuration

The workflow is stored in:

```text
.github/
└── workflows/
    └── deploy.yml
```

The workflow is triggered when code is pushed to the `main` branch.

A simplified configuration is:

```yaml
name: Build, Publish and Deploy

on:
  push:
    branches:
      - 'main'
```

Using the `main` branch as the deployment branch means that merging or pushing a change to `main` automatically starts a production deployment.

This keeps the deployment process simple:

```text
Change code
    │
    ▼
Commit
    │
    ▼
Push / merge to main
    │
    ▼
GitHub Actions
    │
    ▼
Production deployment
```

---

## 3. Environment Variables

The workflow defines the container registry and image name once at workflow level:

```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
```

`${{ github.repository }}` automatically resolves to the GitHub repository name.

For this project, the resulting image name is:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager
```

The workflow therefore does not need to hard-code the repository owner and name in multiple places.

---

## 4. Build and Publish Job

The first job is responsible for creating the Docker image and publishing it to GHCR.

```yaml
jobs:
  push_to_registry:
    name: Build and publish Docker image
    runs-on: ubuntu-latest
```

The job runs on a temporary GitHub-hosted Ubuntu runner.

The runner is not the production server. It is an isolated environment provided by GitHub specifically for executing the workflow.

The high-level process is:

```text
GitHub-hosted runner
        │
        ▼
Check out repository
        │
        ▼
Set up Docker
        │
        ▼
Authenticate with GHCR
        │
        ▼
Build Docker image
        │
        ▼
Push image to GHCR
```

---

## 5. GitHub Actions Permissions

The build job requires permission to read the repository and publish packages:

```yaml
permissions:
  contents: read
  packages: write
```

`contents: read` allows the workflow to check out the repository contents.

`packages: write` allows the workflow to publish the Docker image to GHCR.

These permissions are granted to the automatically generated GitHub Actions workflow token.

The workflow does **not** need a manually created `GITHUB_TOKEN` secret.

---

## 6. Checking Out the Repository

The first step checks out the repository onto the GitHub Actions runner:

```yaml
- name: Check out repository
  uses: actions/checkout@v6
```

This makes the application source code, Dockerfile, `pyproject.toml`, `uv.lock` and other required files available to Docker.

The Docker build therefore runs against the same source code that triggered the workflow.

---

## 7. Docker Build Environment

The workflow configures Docker Buildx:

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v4
```

Buildx provides the Docker build functionality used by the workflow.

QEMU is also configured:

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v4
```

This allows the Docker build environment to support architectures other than the runner's native architecture if required.

For the current application, the important purpose is to provide a standard Docker build environment that can be reused if the deployment architecture changes in the future.

---

## 8. Authenticating with GHCR

Before the image can be published, the GitHub Actions runner authenticates with GHCR:

```yaml
- name: Log in to GHCR
  uses: docker/login-action@v4
  with:
    registry: ${{ env.REGISTRY }}
    username: ${{ github.actor }}
    password: ${{ github.token }}
```

The important distinction is that this authentication uses the **GitHub Actions workflow token**.

GitHub automatically creates this token for each workflow run.

It is therefore not necessary to create and store a permanent `GITHUB_TOKEN` secret.

The authentication flow is:

```text
GitHub Actions
      │
      │ automatically generated token
      ▼
    GHCR
      │
      ▼
Allow image publication
```

The token is scoped to the workflow and is not intended to be used as a permanent credential outside GitHub Actions.

---

## 9. Building and Publishing the Image

The Docker image is built and pushed using:

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v7
  with:
    context: .
    push: true
    tags: |
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

The build context is the root of the repository:

```text
context: .
```

`push: true` tells Docker to publish the resulting image to GHCR rather than only creating it locally on the GitHub runner.

Two image tags are created.

### `latest`

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

This represents the current production image.

The production Docker Compose configuration uses this tag when pulling the application image.

### Git commit SHA

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:<commit-sha>
```

`${{ github.sha }}` contains the commit SHA associated with the workflow run.

This provides an immutable reference to the exact source version used to create the image.

For example:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:8f31c7...
```

This is useful when investigating which version of the application produced a particular deployment.

---

## 10. GitHub Actions Build Cache

The workflow uses the GitHub Actions cache:

```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

Docker can therefore reuse layers from previous builds where possible.

This is particularly useful because the Dockerfile is structured so that dependency installation can be cached separately from the application source:

```text
pyproject.toml
uv.lock
     │
     ▼
Install dependencies
     │
     ▼
Copy application source
```

If only application source code changes, Docker does not necessarily need to rebuild the dependency layers.

The cache therefore reduces the time required to produce subsequent images.

---

## 11. Deploy to Oracle VM

Once the image has successfully been built and published, the second job starts:

```yaml
deploy_via_ssh:
  name: Deploy to Oracle VM
  needs: push_to_registry
  runs-on: ubuntu-latest
```

The important part is:

```yaml
needs: push_to_registry
```

This means the deployment job only runs if the image build and publication job succeeds.

The dependency is therefore:

```text
Build and publish
       │
       │ success
       ▼
Deploy to Oracle VM
```

If the Docker build or GHCR publication fails, the deployment stage is not started.

---

## 12. Production Secrets

The deployment workflow needs to provide configuration values to the production environment.

Sensitive values are stored as **GitHub Actions secrets** rather than being committed to the repository.

Examples include:

```text
POSTGRES_PASSWORD
SOLIS_KEY_ID
SOLIS_KEY_SECRET
SOLIS_INVERTER_SN
PINGRAM_API_KEY
DESTINATION_EMAIL
DEPLOY_HOST
DEPLOY_USERNAME
DEPLOY_KEY
GHCR_USERNAME
GHCR_TOKEN
```

The exact set of secrets should match the production configuration used by the application.

The important principle is:

```text
Git repository
     │
     ├── Application code
     ├── Dockerfile
     └── Deployment configuration

GitHub Secrets
     │
     └── Sensitive production values
```

Secrets are injected into the workflow when required rather than being stored in the Docker image or committed to Git.

---

## 13. Creating the Production `.env`

The deployment job creates the production `.env` file from GitHub Actions secrets:

```yaml
- name: Create .env file
  run: |
    echo "Generating .env file"

    cat > .env <<EOF
    POSTGRES_USER=${{ secrets.POSTGRES_USER }}
    POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
    POSTGRES_DB=${{ secrets.POSTGRES_DB }}

    SOLIS_KEY_ID=${{ secrets.SOLIS_KEY_ID }}
    SOLIS_KEY_SECRET=${{ secrets.SOLIS_KEY_SECRET }}
    SOLIS_INVERTER_SN=${{ secrets.SOLIS_INVERTER_SN }}

    PINGRAM_API_KEY=${{ secrets.PINGRAM_API_KEY }}
    DESTINATION_EMAIL=${{ secrets.DESTINATION_EMAIL }}
    EOF
```

This file is created only on the GitHub Actions runner.

It is then transferred to the Oracle VM as part of the deployment.

The Docker image itself does not contain these secrets.

This separation is important because the same Docker image can be used in different environments without rebuilding it with different credentials.

---

## 14. Copying Deployment Files to the VM

The deployment files are transferred to the Oracle VM using SCP:

```yaml
- name: Copy deployment files to target server
  uses: appleboy/scp-action@v1
  with:
    host: ${{ secrets.DEPLOY_HOST }}
    username: ${{ secrets.DEPLOY_USERNAME }}
    port: 22
    key: ${{ secrets.DEPLOY_KEY }}
    source: "docker-compose.yaml,.env"
    target: "~/.deploy/${{ github.event.repository.name }}/"
```

The workflow therefore transfers:

```text
docker-compose.yaml
.env
```

to the deployment directory on the VM.

The Docker image is **not** copied through SCP.

Instead, the VM pulls the image directly from GHCR.

---

## 15. SSH Deployment

After the configuration files have been copied, GitHub Actions connects to the VM using SSH:

```yaml
- name: Deploy application via SSH
  uses: appleboy/ssh-action@v1
```

The SSH connection is authenticated using the deployment SSH key stored as a GitHub Actions secret.

The commands executed on the VM are effectively:

```text
GitHub Actions
      │
      │ SSH
      ▼
Oracle VM
      │
      ├── docker login
      ├── docker compose pull
      ├── docker compose up -d
      └── docker image prune
```

---

## 16. Authenticating the Oracle VM with GHCR

The Oracle VM needs its **own** authentication to GHCR because the production image is private.

This is separate from the authentication used by the GitHub Actions build job.

The deployment workflow passes the GHCR credentials to the SSH session:

```yaml
env:
  GHCR_USERNAME: ${{ secrets.GHCR_USERNAME }}
  GHCR_TOKEN: ${{ secrets.GHCR_TOKEN }}
```

The VM then authenticates with GHCR:

```bash
echo "$GHCR_TOKEN" | docker login \
  ghcr.io \
  --username "$GHCR_USERNAME" \
  --password-stdin
```

The distinction is:

```text
GitHub Actions runner
        │
        │ GitHub Actions token
        ▼
       GHCR
        ▲
        │
        │ GHCR read credentials
        │
   Oracle VM
```

The GitHub Actions token is used to **publish** the image.

The Oracle VM uses separate credentials to **pull** the private image.

These are two different authentication requirements.

---

## 17. Pulling the New Image

After authentication, the workflow changes to the deployment directory:

```bash
cd ~/.deploy/${{ github.event.repository.name }}
```

It then runs:

```bash
docker compose pull
```

Docker Compose reads the image configured in `docker-compose.yaml`:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

and pulls the current version from GHCR.

The image is therefore not built on the Oracle VM.

The VM only needs to download the already-built image.

```text
GitHub Actions
      │
      ▼
Build image
      │
      ▼
GHCR
      │
      │ docker compose pull
      ▼
Oracle VM
```

---

## 18. Starting the Application

Once the new image has been pulled, the workflow runs:

```bash
docker compose up -d
```

Docker Compose creates or recreates the required services using the new image where necessary.

The production services are therefore updated without manually starting each container.

The process is:

```text
New image in GHCR
        │
        ▼
docker compose pull
        │
        ▼
docker compose up -d
        │
        ▼
Updated application containers
```

Existing PostgreSQL data remains stored in the persistent Docker volume and is not part of the application image.

---

## 19. Cleaning Up Old Images

The workflow performs a basic Docker image cleanup:

```bash
docker image prune -f
```

This removes unused Docker images from the Oracle VM.

Without periodic cleanup, old application images can accumulate over time and consume disk space.

The command only removes images that Docker considers unused.

---

## 20. Deployment Status

The final command displays the status of the Compose services:

```bash
docker compose ps
```

This provides an immediate indication of whether the expected containers are running.

The workflow therefore finishes with a basic deployment verification:

```text
docker compose pull
        │
        ▼
docker compose up -d
        │
        ▼
docker image prune -f
        │
        ▼
docker compose ps
```

This does not replace application-level verification, but it confirms that Docker Compose has attempted to start the production stack.

---

## 21. Complete Workflow

The complete workflow can be represented as:

```yaml
name: Build, Publish and Deploy

on:
  push:
    branches:
      - 'main'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:

  push_to_registry:
    name: Build and publish Docker image
    runs-on: ubuntu-latest

    permissions:
      contents: read
      packages: write

    steps:

      - name: Check out repository
        uses: actions/checkout@v6

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4

      - name: Log in to GHCR
        uses: docker/login-action@v4
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ github.token }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v7
        with:
          context: .
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  deploy_via_ssh:
    name: Deploy to Oracle VM
    needs: push_to_registry
    runs-on: ubuntu-latest

    steps:

      - name: Check out repository
        uses: actions/checkout@v6

      - name: Create .env file
        run: |
          echo "Generating .env file"

          cat > .env <<EOF
          POSTGRES_USER=${{ secrets.POSTGRES_USER }}
          POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
          POSTGRES_DB=${{ secrets.POSTGRES_DB }}

          SOLIS_KEY_ID=${{ secrets.SOLIS_KEY_ID }}
          SOLIS_KEY_SECRET=${{ secrets.SOLIS_KEY_SECRET }}
          SOLIS_INVERTER_SN=${{ secrets.SOLIS_INVERTER_SN }}

          PINGRAM_API_KEY=${{ secrets.PINGRAM_API_KEY }}
          DESTINATION_EMAIL=${{ secrets.DESTINATION_EMAIL }}
          EOF

      - name: Copy deployment files to target server
        uses: appleboy/scp-action@v1
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USERNAME }}
          port: 22
          key: ${{ secrets.DEPLOY_KEY }}
          source: "docker-compose.yaml,.env"
          target: "~/.deploy/${{ github.event.repository.name }}/"

      - name: Deploy application via SSH
        uses: appleboy/ssh-action@v1
        env:
          GHCR_USERNAME: ${{ secrets.GHCR_USERNAME }}
          GHCR_TOKEN: ${{ secrets.GHCR_TOKEN }}

        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USERNAME }}
          port: 22
          key: ${{ secrets.DEPLOY_KEY }}
          envs: GHCR_USERNAME,GHCR_TOKEN

          script: |
            set -e

            echo "$GHCR_TOKEN" | docker login \
              ghcr.io \
              --username "$GHCR_USERNAME" \
              --password-stdin

            cd ~/.deploy/${{ github.event.repository.name }}

            echo "Pulling latest application image..."
            docker compose pull

            echo "Starting application..."
            docker compose up -d

            echo "Removing unused images..."
            docker image prune -f

            echo "Deployment status:"
            docker compose ps
```

---

## 22. GitHub Actions Secrets Reference

The following secrets are required by the deployment workflow.

| Secret              | Purpose                        |
| ------------------- | ------------------------------ |
| `POSTGRES_USER`     | PostgreSQL username            |
| `POSTGRES_PASSWORD` | PostgreSQL password            |
| `POSTGRES_DB`       | PostgreSQL database name       |
| `SOLIS_KEY_ID`      | SolisCloud API key ID          |
| `SOLIS_KEY_SECRET`  | SolisCloud API key secret      |
| `SOLIS_INVERTER_SN` | Solis inverter serial number   |
| `PINGRAM_API_KEY`   | Pingram API key                |
| `DESTINATION_EMAIL` | Notification destination       |
| `DEPLOY_HOST`       | Oracle VM hostname/IP          |
| `DEPLOY_USERNAME`   | SSH username                   |
| `DEPLOY_KEY`        | SSH private key                |
| `GHCR_USERNAME`     | GHCR account used by the VM    |
| `GHCR_TOKEN`        | GHCR credential used by the VM |

`GITHUB_TOKEN` is **not** included in this list because GitHub automatically creates it for each workflow run.

The workflow uses it when publishing the Docker image to GHCR.

---

## 23. Authentication Summary

There are two separate authentication paths in the deployment:

### GitHub Actions → GHCR

Used to publish the Docker image.

```text
GitHub Actions
      │
      │ automatically generated GITHUB_TOKEN
      ▼
     GHCR
      │
      ▼
Publish image
```

### Oracle VM → GHCR

Used to pull the private Docker image.

```text
Oracle VM
      │
      │ GHCR_USERNAME + GHCR_TOKEN
      ▼
     GHCR
      │
      ▼
Pull image
```

These credentials should not be confused.

The GitHub Actions token is temporary and associated with the workflow.

The VM requires a separate credential because it is an external production system.

---

## 24. Why GHCR Is Used

The application Docker image is stored in the GitHub Container Registry rather than being built directly on the Oracle VM.

This provides a clear separation between:

```text
Source code
     │
     ▼
GitHub
     │
     ▼
Build environment
     │
     ▼
GHCR
     │
     ▼
Production VM
```

The Oracle VM therefore does not need the application source code or the Python build environment required to create the image.

It only needs Docker and access to GHCR.

This also means that the exact same image that was built and tested by the GitHub Actions process is the image deployed to production.

---

## 25. Deployment Responsibilities

Each component has a specific responsibility:

| Component      | Responsibility                                   |
| -------------- | ------------------------------------------------ |
| GitHub         | Stores source code and workflow configuration    |
| GitHub Actions | Builds and deploys the application               |
| Docker Buildx  | Builds the Docker image                          |
| GHCR           | Stores the private Docker image                  |
| Oracle VM      | Hosts the production application                 |
| Docker Compose | Manages production containers                    |
| Dagster        | Manages application execution and scheduled runs |
| PostgreSQL     | Stores Dagster metadata                          |

GitHub Actions therefore handles the **deployment process**, but it does not manage the application's runtime execution.

Once deployment has completed, Docker Compose and Dagster take over.

---

## 26. End-to-End Deployment

The complete process is:

```text
                    Developer
                        │
                        │ push to main
                        ▼
                   GitHub
                        │
                        ▼
                GitHub Actions
                        │
             ┌──────────┴──────────┐
             │                     │
             ▼                     │
       Checkout source             │
             │                     │
             ▼                     │
       Build Docker image          │
             │                     │
             ▼                     │
       Authenticate with GHCR      │
             │                     │
             ▼                     │
       Push image to GHCR          │
             │                     │
             └──────────┐          │
                        ▼          │
                  SSH to VM        │
                        │          │
                        ▼          │
                 Copy .env and     │
                 Compose config    │
                        │          │
                        ▼          │
                 Docker login      │
                        │          │
                        ▼          │
                 docker compose    │
                      pull         │
                        │          │
                        ▼          │
                 docker compose    │
                       up -d       │
                        │
                        ▼
                  Production
                  application
```

The resulting deployment model is deliberately simple:

**GitHub Actions builds it → GHCR stores it → the Oracle VM pulls it → Docker Compose runs it.**

This document covers the GitHub Actions portion of the deployment. The Docker, Docker Compose and Dagster runtime architecture is documented separately in **Deploying a Dagster Application with Docker**.

---

Actions used in the workflow:

- [actions/checkout@v6](https://github.com/actions/checkout)
- [docker/setup-qemu-action@v4](https://github.com/docker/setup-qemu-action)
- [docker/setup-buildx-action@v4](https://github.com/docker/setup-buildx-action)
- [docker/login-action@v4](https://github.com/docker/login-action)
- [docker/build-push-action@v7](https://github.com/docker/build-push-action)
- [appleboy/scp-action@v1](https://github.com/appleboy/scp-action)
- [appleboy/ssh-action@v1](https://github.com/appleboy/ssh-action)
