# Oracle VM Docker Host Setup

This document describes the setup of the Oracle Cloud VM used as the Docker host for the application.

The VM is a general-purpose Docker host rather than a host dedicated exclusively to the Solis application. Docker Compose is used to run the application services, while GitHub Actions is responsible for deploying new container images.

## 1. Oracle Cloud Instance

The production Docker host is an Oracle Cloud Infrastructure Compute instance.

### Instance configuration

| Setting           | Value                                                 |
| ----------------- | ----------------------------------------------------- |
| Instance name     | `p_y_t_h_e_c - docker-app-host`                       |
| Capacity type     | On-demand                                             |
| Shape             | `VM.Standard.A1.Flex`                                 |
| OCPUs             | 2                                                     |
| Memory            | 12 GB                                                 |
| Network bandwidth | 2 Gbps                                                |
| Architecture      | ARM64 / AArch64                                       |
| Operating system  | Ubuntu 26.04 Minimal                                  |
| Image             | `Canonical-Ubuntu-26.04-Minimal-aarch64-2026.08.17-0` |
| Primary VNIC      | `p_y_t_h_e_c - docker-app-host-vnic`                  |

The ARM64 architecture is important because the Oracle A1 instance uses an ARM-based CPU.

The selected Ubuntu image is:

`Canonical-Ubuntu-26.04-Minimal-aarch64-2026.08.17-0`

The VM should therefore run ARM64-compatible Docker images natively.

## 2. SSH Access

An SSH key pair is used to access the VM.

The local private key is:

```text
~/.ssh/p_y_t_h_e_c-docker-app-host-ssh-key
```

The corresponding public key is added to the Oracle instance during VM creation.

The private key should have restricted permissions:

```bash
chmod 600 ~/.ssh/p_y_t_h_e_c-docker-app-host-ssh-key
```

The private key must never be committed to the repository.

It is also used by GitHub Actions to establish the SSH connection to the production VM.

## 3. Network Access

The Oracle VCN security list must allow the traffic required by the host.

### Required ingress

| Port | Protocol | Purpose                                  |
| ---: | -------- | ---------------------------------------- |
|   22 | TCP      | SSH access and GitHub Actions deployment |
| 3000 | TCP      | Dagster webserver                        |

Port `4000`, used by the Dagster gRPC code server, does not need to be exposed publicly.

The gRPC server is accessed internally through the Docker network.

PostgreSQL port `5432` is also not exposed publicly. PostgreSQL is only accessible to the containers on the Docker network.

## 4. Operating System Setup

After connecting to the VM, update the operating system:

```bash
sudo apt update
sudo apt upgrade -y
```

Confirm the architecture:

```bash
uname -m
```

Expected result:

```text
aarch64
```

This confirms that the Oracle VM is running on ARM64.

## 5. Docker Installation

Install Docker using the official Docker installation instructions appropriate for the selected Ubuntu release.

After installation, verify Docker:

```bash
docker --version
```

Verify Docker Compose:

```bash
docker compose version
```

The application uses the modern Docker Compose plugin:

```text
docker compose
```

rather than the legacy standalone:

```text
docker-compose
```

The legacy `docker-compose` binary should not be manually installed on the ARM64 host.

## 6. Docker Architecture

The Oracle VM is ARM64, but the application image is built as a multi-platform image.

GitHub Actions builds:

```text
linux/amd64
linux/arm64
```

and publishes both variants under the same GHCR image tag.

For example:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

Conceptually:

```text
                         GHCR
                          │
             multi-platform image
                          │
                ┌─────────┴─────────┐
                │                   │
          linux/amd64          linux/arm64
                │                   │
                │                   ▼
                │             Oracle A1 VM
                │
          x86-64 systems
```

When Docker pulls the image, it selects the variant matching the host architecture. Docker documents this behaviour as part of its multi-platform image support.

Therefore the Oracle ARM64 host does not need to run the AMD64 image through emulation.

## 7. Multi-Platform GitHub Actions Build

The GitHub Actions workflow uses Docker Buildx to publish both architectures:

```yaml
- name: Build and push Docker image
  uses: docker/build-push-action@v7
  with:
    context: .
    push: true
    platforms: linux/amd64,linux/arm64
    tags: |
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
      ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

QEMU is configured in the workflow before the build:

```yaml
- name: Set up QEMU
  uses: docker/setup-qemu-action@v4
```

and Docker Buildx is configured with:

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v4
```

Docker officially supports this GitHub Actions pattern for multi-platform builds.

The important point is that QEMU is used by the **GitHub Actions build environment**, not by the production Oracle VM.

## 8. No Production binfmt Installation Required

The previous deployment approach used:

```bash
docker run --privileged --rm tonistiigi/binfmt --install all
```

to allow an ARM64 host to run an AMD64 image through emulation.

This is no longer required.

The application is now published as a native ARM64 image, so the Oracle VM can run the application natively.

The production deployment should therefore **not** install additional `binfmt` emulators merely to run this application.

This also avoids the unnecessary performance overhead associated with emulating another CPU architecture.

## 9. Deployment Directory

The deployment files are stored under:

```text
~/.deploy/<repository-name>/
```

For this application:

```text
~/.deploy/solis_energy_manager/
```

The deployment directory contains the production Docker Compose configuration and generated environment file.

Example:

```text
~/.deploy/solis_energy_manager/
├── docker-compose.yaml
└── .env
```

The `.env` file contains production configuration and secrets and must not be committed to Git.

## 10. GitHub Actions SSH Configuration

GitHub Actions connects to the VM using the SSH private key stored in the repository's GitHub Actions secrets.

The deployment configuration uses:

```text
DEPLOY_HOST
DEPLOY_USERNAME
DEPLOY_KEY
```

Where:

* `DEPLOY_HOST` = public IP address of the Oracle VM.
* `DEPLOY_USERNAME` = `ubuntu`.
* `DEPLOY_KEY` = private SSH key corresponding to the public key installed on the VM.

The GitHub Actions runner uses this key to:

1. Copy deployment files to the VM.
2. Connect to the VM over SSH.
3. Authenticate Docker to GHCR.
4. Pull the new application image.
5. Restart the Docker Compose stack.

## 11. GHCR Authentication

The application image is stored as a private package in GitHub Container Registry.

The Oracle VM therefore needs permission to pull the image.

The deployment process authenticates Docker to GHCR before running:

```bash
docker compose pull
```

The GHCR authentication used by the VM is separate from the `GITHUB_TOKEN` used by GitHub Actions to publish the image.

The GitHub Actions workflow should not treat `GITHUB_TOKEN` as a permanent credential installed on the VM.

## 12. Docker Compose Deployment

The production application is started using:

```bash
docker compose up -d
```

Before this, the deployment process pulls the latest image:

```bash
docker compose pull
```

Because the image is multi-platform, the ARM64 Oracle VM automatically receives the `linux/arm64` variant.

The Compose stack consists of:

```text
┌──────────────────────────────────────┐
│          Oracle ARM64 VM             │
│                                      │
│  Docker                              │
│                                      │
│  ┌────────────────────────────────┐  │
│  │ Docker Compose                 │  │
│  │                                │  │
│  │ PostgreSQL                     │  │
│  │ Dagster code server            │  │
│  │ Dagster webserver              │  │
│  │ Dagster daemon                 │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

## 13. Application Image

The production image is:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest
```

A commit-specific image is also published:

```text
ghcr.io/p-y-t-h-e-c/solis_energy_manager:<commit-sha>
```

The `latest` tag is used by the production Compose configuration.

The commit SHA tag provides an immutable reference to the image produced from a particular Git commit.

## 14. General-Purpose Docker Host

This VM is intended to be a general-purpose Docker host.

For this reason, deployment scripts must avoid commands that indiscriminately remove all Docker resources.

Do not use:

```bash
docker rm -vf $(docker ps -aq)
```

or:

```bash
docker rmi -f $(docker images -aq)
```

These commands can remove unrelated containers and images running on the host.

Deployment cleanup should be limited to resources that are no longer required by the application.

For example:

```bash
docker image prune -f
```

is appropriate for removing unused dangling images without indiscriminately deleting every image on the host.

## 15. ARM64 Compatibility

The application image itself is now explicitly tested by the deployment process on the ARM64 production environment.

The following components must remain compatible with ARM64:

* Python base image.
* Python dependencies.
* Dagster.
* Docker image layers.
* Any native Python packages.
* Any executable binaries included in the image.

If a dependency does not provide an ARM64-compatible distribution, the multi-platform GitHub Actions build may fail.

This is preferable to discovering the incompatibility only after deployment.

## 16. Verify the Image Architecture

After deployment, the image architecture can be inspected on the Oracle VM:

```bash
docker image inspect \
  ghcr.io/p-y-t-h-e-c/solis_energy_manager:latest \
  --format '{{.Architecture}}/{{.Os}}'
```

On the Oracle A1 host, the expected result is:

```text
arm64/linux
```

The multi-platform manifest can also be inspected using Docker tooling if required.

## 17. Verify the Docker Host

Useful checks after setup include:

```bash
uname -m
docker --version
docker compose version
docker info
```

Expected architecture:

```text
aarch64
```

Verify the application containers:

```bash
docker compose ps
```

The expected services are:

```text
docker_postgresql_db
solis_energy_manager_code
solis_energy_manager_webserver
solis_energy_manager_daemon
```

## 18. Deployment Verification

After deployment:

```bash
docker compose ps
```

Check application logs:

```bash
docker compose logs --tail=100
```

Check the Dagster webserver:

```text
http://<VM_PUBLIC_IP>:3000
```

The Dagster UI should load successfully.

The code server should be available internally on port `4000`, but that port should not be exposed through the Oracle VCN.

## 19. Production Architecture

The resulting architecture is:

```text
                           GitHub

                             │
                             ▼
                     GitHub Actions
                             │
                     Buildx + QEMU
                             │
             ┌───────────────┴───────────────┐
             │                               │
       linux/amd64                       linux/arm64
             │                               │
             └───────────────┬───────────────┘
                             │
                             ▼
                            GHCR
                             │
                    authenticated pull
                             │
                             ▼
              p_y_t_h_e_c - docker-app-host
                    Oracle ARM64 VM
                             │
                       Docker Compose
                             │
             ┌───────────────┼───────────────┐
             ▼               ▼               ▼
         PostgreSQL       Webserver        Daemon
                             │               │
                             ▼               │
                        Code Server          │
                                             │
                                      DockerRunLauncher
                                             │
                                             ▼
                                      Ephemeral run
                                        container
```

## 20. Local Development

The production image architecture does not change the local development workflow.

Local development continues to use:

```text
solis_energy_manager:local
```

through the local Compose override.

Start the local environment with:

```bash
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.local.yaml \
  up --build
```

The local override builds the image locally rather than pulling the production image from GHCR.

Therefore the local development environment remains independent of the production registry architecture.

For example:

```text
LOCAL DEVELOPMENT

Source code
     │
     ▼
docker compose --build
     │
     ▼
solis_energy_manager:local
     │
     ├── Code server
     ├── Webserver
     └── Daemon
```

The production environment instead uses:

```text
PRODUCTION

GitHub
   │
   ▼
GitHub Actions
   │
   ▼
GHCR
   │
   ▼
linux/arm64 image
   │
   ▼
Oracle A1
```

This separation allows features to continue being developed and tested locally without requiring every development build to be published to GHCR.

## 21. Clean Local Rebuild

If a completely clean local build is required:

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

The local image remains:

```text
solis_energy_manager:local
```

and does not interfere with the production GHCR image.

## 22. Final Setup Checklist

### Oracle Cloud

* [x] Instance created.
* [x] Instance name: `p_y_t_h_e_c - docker-app-host`.
* [x] Primary VNIC: `p_y_t_h_e_c - docker-app-host-vnic`.
* [x] `VM.Standard.A1.Flex`.
* [x] 2 OCPUs.
* [x] 12 GB memory.
* [x] ARM64 / AArch64.
* [x] Ubuntu 26.04 Minimal.
* [x] `Canonical-Ubuntu-26.04-Minimal-aarch64-2026.08.17-0`.
* [x] SSH access configured.
* [x] Port 22 available.
* [x] Port 3000 available.
* [x] PostgreSQL port 5432 not publicly exposed.
* [x] Docker installed.
* [x] Docker Compose plugin installed.

### Docker

* [x] Docker runs natively on ARM64.
* [x] Production image supports ARM64.
* [x] Production image also supports AMD64.
* [x] No production `binfmt` installation required.
* [x] No forced `linux/amd64` platform in Compose.
* [x] General-purpose host protected from global Docker cleanup commands.

### GitHub Actions

* [x] Docker Buildx configured.
* [x] QEMU configured for multi-platform builds.
* [x] Image built for `linux/amd64`.
* [x] Image built for `linux/arm64`.
* [x] Multi-platform image pushed to GHCR.
* [x] `latest` tag published.
* [x] Commit SHA tag published.
* [x] Oracle VM authenticated to GHCR.
* [x] Docker Compose pulls the appropriate platform automatically.

### Application

* [x] Dagster code server running.
* [x] Dagster webserver running.
* [x] Dagster daemon running.
* [x] PostgreSQL running.
* [x] DockerRunLauncher configured.
* [x] Local development remains available through the local Compose override.
