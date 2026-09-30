# Project Setup

## Prerequisites

The project uses **Python 3.13** and **uv** for Python version and dependency management.

Dagster currently supports Python 3.10 and later, with Python 3.13 recommended for new projects.

Dagster also recommends using `uv` for project and dependency management.

## Installing `uv`

The quickest and most straightforward way to install `uv` is to use the standalone installer.

For Linux or macOS, run:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For Windows PowerShell, run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Once installed, verify that `uv` is available:

```bash
uv --version
```

Installing `uv` also provides the `uvx` command, which can be used to execute Python-based command-line tools without installing them globally.

### Installing Python with `uv`

If the required Python version is not already available locally, `uv` can install and manage Python versions.

For example:

```bash
uv python install 3.13
```

You can verify the available Python versions with:

```bash
uv python list
```

`uv` can automatically detect an existing Python installation, so installing Python through `uv` is not required if a suitable version is already available.

## Creating a Dagster project

Once `uv` is installed, a new Dagster project can be scaffolded using the `create-dagster` CLI.

### Creating a new project

To create a new Dagster project in a new directory:

```bash
uvx create-dagster@latest project my-project
```

Where:

* `my-project` is the name of the project directory to be created.
* `create-dagster@latest` ensures that the latest version of the Dagster project scaffolder is used.

The scaffolder creates the recommended Dagster project structure and dependencies. When prompted to run `uv sync`, select **Yes** to create the project environment and install the dependencies.

The resulting project structure is similar to:

```text
my-project/
├── src/
│   └── my_project/
│       ├── __init__.py
│       ├── definitions.py
│       ├── defs/
│       │   └── __init__.py
│       └── components/
│           └── __init__.py
├── tests/
│   └── __init__.py
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

The exact structure may vary slightly between Dagster versions. The `defs/` directory is intended for Dagster definitions, while `components/` can contain custom Dagster component types.

### Scaffolding Dagster into an existing repository

If the repository already exists, for example a new Git repository that has already been created and cloned locally, Dagster can be scaffolded directly into the current directory:

```bash
uvx create-dagster@latest project .
```

Using `.` as the project path tells the Dagster scaffolder to create the project in the current working directory rather than creating an additional nested directory.

This is useful when starting with an otherwise empty repository because it allows the Dagster project structure to be created directly within the repository.

For example:

```text
my-project/
├── src/
├── tests/
├── pyproject.toml
├── README.md
└── uv.lock
```

rather than:

```text
my-project/
└── my-project/
    ├── src/
    ├── tests/
    ├── pyproject.toml
    └── ...
```

### Setting up Dagster in an existing Python project

If the repository already contains Python code and configuration that should be preserved, it may be preferable to add Dagster manually rather than running the scaffolder.

With an existing `uv` project, install the required Dagster packages with:

```bash
uv add dagster dagster-webserver dagster-dg-cli
```

This approach provides more control over the existing project structure and avoids potentially conflicting with existing configuration.

## Working with the Dagster project

### Activating the virtual environment

If the project was created using the Dagster scaffolder and `uv`, the virtual environment will normally have been created as part of the initial `uv sync`.

Activate it using:

| OS            | Command                     |
| ------------- | --------------------------- |
| macOS / Linux | `source .venv/bin/activate` |
| Windows       | `.venv\Scripts\activate`    |

Verify the Dagster CLI installation:

```bash
dg --version
```

### Running Dagster locally

From the project root, start the Dagster development server:

```bash
dg dev
```

The Dagster UI will be available at:

<!-- markdown-link-check-disable-next-line -->
<http://localhost:3000>

The `dg` CLI is the current Dagster development CLI used by the scaffolded project.

## Managing Python dependencies

### Adding a dependency

To add a new Python dependency to the project:

```bash
uv add <package_name>
```

For example:

```bash
uv add requests
```

This updates the project's `pyproject.toml`, lock file, and virtual environment.

For development-only dependencies:

```bash
uv add --dev <package_name>
```

### Synchronising dependencies

To synchronise the virtual environment with the project's dependency configuration and lock file:

```bash
uv sync
```

If the `.venv` directory does not exist, `uv sync` will create it automatically.

### Updating dependencies

To update a specific dependency:

```bash
uv lock --upgrade-package <package_name>
```

To update all dependencies:

```bash
uv lock --upgrade
```

After changing the lock file, synchronise the environment:

```bash
uv sync
```

### Checking installed dependencies

To check a specific installed package:

```bash
uv pip show <package_name>
```

For example:

```bash
uv pip show dagster
```

To list all installed packages:

```bash
uv pip list
```

To list packages with newer versions available:

```bash
uv pip list --outdated
```

## Dagster project structure

The scaffolded Dagster project provides a structure in which the main project configuration and Dagster definitions are separated.

The `definitions.py` file acts as the central entry point for the Dagster project. It should primarily bootstrap the project by bringing together assets, jobs, schedules, sensors, resources and other definitions rather than containing business logic.

Dagster definitions can be organised within the `defs/` directory according to the requirements of the project. For example:

```text
src/
└── my_project/
    ├── definitions.py
    └── defs/
        ├── assets/
        ├── jobs/
        ├── schedules/
        ├── sensors/
        └── resources/
```

This keeps the project modular and makes individual Dagster definitions easier to discover and maintain.

## Scaffolding Dagster assets

New Dagster definitions can be scaffolded using the `dg` CLI.

For example, to create an asset definition:

```bash
dg scaffold defs dagster.asset assets.py
```

This creates the corresponding definition within the project's `defs/` directory.

## Changing the Python version

To check the Python version currently being used:

```bash
python --version
```

If a different Python version is required, ensure that it is available through `uv`:

```bash
uv python install <required_version>
```

For example:

```bash
uv python install 3.13
```

The project can then be configured to use the required version and the environment recreated as necessary.

## Further reading

For additional information, refer to the official documentation:

* [Dagster Documentation](https://docs.dagster.io/)
* [Dagster Installation](https://docs.dagster.io/getting-started/installation)
* [Dagster Quickstart](https://docs.dagster.io/getting-started/quickstart)
* [Creating a New Dagster Project](https://docs.dagster.io/guides/build/projects/creating-a-new-project)
* [Dagster `create-dagster` CLI](https://docs.dagster.io/api/clis/create-dagster)
* [`uv` Documentation](https://docs.astral.sh/uv/)
* [`uv` Installation](https://docs.astral.sh/uv/getting-started/installation/)
* [Managing Python Versions with `uv`](https://docs.astral.sh/uv/guides/install-python/)
* [Working on Projects with `uv`](https://docs.astral.sh/uv/guides/projects/)
