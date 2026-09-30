# Project Setup

## Getting started

### Prerequisites

The project currently uses **Python 3.13** and **uv** for dependency management.

If `uv` is not already installed, follow the [official `uv` installation documentation](https://docs.astral.sh/uv/getting-started/installation/).

You can verify the installation with:

```bash
uv --version
```

### Installing dependencies

There are two options for setting up the project dependencies.

#### Option 1: `uv`

This is the recommended approach.

From the project root, create the virtual environment and install the required dependencies:

```bash
uv sync
```

Then activate the virtual environment:

| OS            | Command                     |
| ------------- | --------------------------- |
| macOS / Linux | `source .venv/bin/activate` |
| Windows       | `.venv\Scripts\activate`    |

#### Option 2: `pip`

If you prefer to use `pip`, create a virtual environment:

```bash
python3 -m venv .venv
```

Then activate the virtual environment:

| OS            | Command                     |
| ------------- | --------------------------- |
| macOS / Linux | `source .venv/bin/activate` |
| Windows       | `.venv\Scripts\activate`    |

Install the project and its development dependencies:

```bash
pip install -e ".[dev]"
```

### Running Dagster

Once the dependencies have been installed and the virtual environment is active, start the Dagster development server:

```bash
dg dev
```
<!-- markdown-link-check-disable-next-line -->
Open <http://localhost:3000> in your browser to access the Dagster UI.

### Adding dependencies

If an additional Python package is required, use `uv` to add it to the project:

```bash
uv add <package_name>
```

This will install the package, add it to `pyproject.toml`, and update `uv.lock`.

For development-only dependencies, use:

```bash
uv add --dev <package_name>
```

### Updating dependencies

To update a specific dependency to the latest compatible version:

```bash
uv lock --upgrade-package <package_name>
```

To update all dependencies:

```bash
uv lock --upgrade
```

After updating the lock file, synchronise the environment:

```bash
uv sync
```

### Project structure

The project follows the Dagster project structure, with Dagster definitions organised under the `defs/` directory.

The main structure is:

```text
.
├── src/
│   └── solis_energy_manager/
│       ├── __init__.py
│       ├── definitions.py
│       └── defs/
│           ├── __init__.py
│           ├── assets/
│           ├── jobs/
│           ├── schedules/
│           ├── sensors/
│           └── resources/
├── tests/
├── .gitignore
├── pyproject.toml
├── README.md
└── uv.lock
```

The `definitions.py` module acts as the entry point for the Dagster project and should remain focused on bootstrapping the project. Business logic and individual Dagster definitions should be kept within the appropriate modules under `defs/`.

### Adding Dagster assets

New Dagster assets can be scaffolded using the Dagster CLI:

```bash
dg scaffold defs dagster.asset assets.py
```

This creates the corresponding asset definition within the `defs/` directory.

### Useful commands

Check the installed version of a specific package:

```bash
uv pip show <package_name>
```

List all installed packages:

```bash
uv pip list
```

List packages for which newer versions are available:

```bash
uv pip list --outdated
```

## Learn more

Further information about Dagster and the tools used by this project can be found in the following documentation:

* [Dagster Documentation](https://docs.dagster.io/)
* [Dagster University](https://courses.dagster.io/)
* [`uv` Documentation](https://docs.astral.sh/uv/)
* [Creating a New Dagster Project](https://docs.dagster.io/guides/build/projects/creating-a-new-project)
* [Working on Projects with `uv`](https://docs.astral.sh/uv/guides/projects/#working-on-projects)
* [Managing Dependencies with `uv`](https://docs.astral.sh/uv/guides/projects/#managing-dependencies)
* [Dagster Concepts](https://docs.dagster.io/getting-started/concepts)
* [Dagster Definitions](https://docs.dagster.io/api/dagster/definitions#dagster.Definitions)
