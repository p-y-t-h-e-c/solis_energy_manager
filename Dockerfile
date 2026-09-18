FROM python:3.13.15-slim-trixie

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    DAGSTER_HOME=/opt/dagster/dagster_home \
    PATH="/opt/dagster/app/.venv/bin:$PATH"

# Dagster instance configuration
RUN mkdir -p ${DAGSTER_HOME}

WORKDIR /opt/dagster/app

# Dagster configuration
COPY dagster.yaml ${DAGSTER_HOME}/dagster.yaml
COPY workspace.yaml .

# Install dependencies first so this layer can be cached
COPY pyproject.toml uv.lock ./

RUN uv sync \
    --frozen \
    --no-install-project \
    --no-dev

# Install the application
COPY src ./src

RUN uv sync \
    --frozen \
    --no-dev

EXPOSE 4000

CMD ["uv", "run", "dagster", "api", "grpc", "-h", "0.0.0.0", "-p", "4000", \
        "-f", "/opt/dagster/app/src/solis_energy_manager/definitions.py"]
