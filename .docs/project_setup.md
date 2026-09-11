# Project Setup

## Prerequisites

- Python, currently ( September 2026 ) Dagster officially supports Python 3.9 through Python 3.14. Python 3.13 is recommended for starting new projects via the create-dagster CLI.
- Dagster recommends using `uv` as a package manager.

## Installing `uv`

The quickest and most straight forward 'uv' installation method is a standalone installer.

For Linux or macOS system this can be downloaded with curl and installed with sh::

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

For Windows PowerShell uv can be installed by executing:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Once installed, you can check that `uv` is available by running:

```bash
uv --version
```

## Scaffolding a Dagster project

Once `uv` is successfully installed.

### A new Dagster project can be scaffolded from scratch using the `uvx` command

```bash
uvx create-dagster@latest project my-project
```

Where:

- my-project → the name of the project directory to be created
- create-dagster@latest → ensures the latest version of the Dagster project scaffolder is used

This command will create a new `my-project/` directory with the required Dagster project structure and boilerplate code:

```bash
.
└── my-project
  ├── .venv
  ├── src
  │   └── my_project
  │       ├── __init__.py
  │       ├── definitions.py
  │       └── defs
  │           └── __init__.py
  ├── tests
  │   └── __init__.py
  ├── .gitignore
  ├── pyproject.toml
  ├── README.md
  └── uv.lock
```

### Dagster can be initiated within already created project / repo directory

This option is recommended for a new, fresh Git repo created in GitLab (just cloned, empty except maybe for README, .gitignore), then:

- You get the full Dagster scaffolding right inside your repo (no extra nesting).
- You don’t risk overwriting anything valuable, since the repo is basically empty.
- You can commit and push the scaffolded Dagster project right away.

This can be achieved by using following command:

```bash
uvx create-dagster@latest project .
```

This will place the Dagster scaffolding directly inside your existing directory instead of creating a new one.

---

For repos that already have existing code/configs, there is manual setup approach which adds Dagster dependencies + create workspace.yaml + repository and asset files. This method is  safer, to avoid conflicts but it may require some further manual interactions to properly set up project structure etc.

This can be done using following command:

```bash
uv add dagster dagster-webserver dagster-dg-cli
```

This command requires `uv` initiated repository with corresponding `pyproject.toml`.

### Updating / Changing Python version if required

To check the current Python version, make sure your virtual environment is activated, then run:

```bash
python --version
```

If the version needs to be changed, ensure it’s available in the `uv` Python list by running:

```bash
uv python install <required_version>
```

For example:

```bash
uv python install 3.13
```

Then, within the project root directory, recreate the virtual environment using:

```bash
uv venv --python <required_version>
```

Finally, reactivate the virtual environment and verify the new version with:

```bash
python --version
```

## Adding new dependency package

To add a new package required by the project run:

```bash
uv add <pkg_name>
```

This will:

- install the latest version of the package in your project virtual environment
- add respective dependency reference into teh the  `pyproject.toml` in format `"package_name>=latest_version"`
- add respective reference into the `uv.lock` file

## Updating a version of the dependency package

If a previously installed dependency package in `pyproject.toml` is specified using the format `"package_name>=latest_version"` instead of being explicitly pinned with `"package_name==latest_version"`, the package can be upgraded to the latest available version with:

```bash
uv lock --upgrade-package <pkg_name>
```

Note: this command only upgrades the specified package.

If there is need to upgrade all packages in one go run:

```bash
uv lock --upgrade
```

This will:

- Reads every dependency package within `pyproject.toml`.
- Resolves the latest compatible versions (according to version specifiers).
- Updates the `uv.lock` accordingly.

## Checking installed dependencies

To verify that a specific package has been successfully installed, run:

```bash
uv pip show <pkg_name>
```

For example:

```bash
uv pip show pandas
```

If the package is installed, this command will display its version, the dependencies it requires and were installed alongside it, and any packages that depend on it.

To view all currently installed dependencies, rather than only a specific one, run:

```bash
uv pip list
```

This will display a list of all installed dependencies along with their versions.

To view only outdated dependencies (those with a newer version available), run:

```bash
uv pip list --outdated
```

This will display the installed dependencies that are outdated, showing both their current version and the latest available version.

## Dagster concepts / components

A Dagster project should follow the defs/ folder structure (especially for medium/large projects).
Some of the known components are:

- defs/assets/ - represents a logical unit of data such as a table, dataset
- defs/jobs/ - represents custom jobs
- defs/schedules/ - schedule definitions
- defs/sensors/ - event-driven triggers
- defs/resources/ - resources like databases, API connections
This structure keeps definitions modular easier to scale and discover.

## Scaffolding Assets structure

Assets are one of the main part of the Dagster `def/component` structure.

Before scaffolding assets file the virtual environments must be activated.
The uv-managed virtual environment should be created within `.venv`. To activate it

- for Linux or macOS system:

```bash
source .venv/bin/activate
```

- or on Windows:

```powershell
.venv\Scripts\activate
```

Once virtual environment activated and active the assets file can be scaffolded with:

```bash
dg scaffold defs dagster.asset assets.py
```

This will add a new file assets.py to the defs directory:

```bash
.
└── my-project
   ├── .venv
   ├── src
   │   └── my_project
   │       ├── __init__.py
   │       ├── definitions.py
   │       └── defs
   │           ├── __init__.py
   │           └── assets.py
   ├── tests
   │   └── __init__.py
   ├── .gitignore
   ├── pyproject.toml
   ├── README.md
   └── uv.lock
```

## Dagster Definitions (or @definitions)

Dagster **definitions** serve as the central configuration that tells Dagster what your project contains.
By default, the file is named `definitions.py` and is located in the `src/your_project_name` directory, alongside the `defs/` folder.

A sample `definitions.py` module:

```python
import dagster as dg
from dagster_gcp.gcs import GCSResource

from .defs.assets import my_gcs_asset

defs = dg.Definitions(
    assets=[my_gcs_asset],
    resources={"gcs": GCSResource(project="my-gcp-project")},
)
```

The `definitions.py` file should be kept **minimal**: it should only bootstrap the project, not contain business logic.

## Running Dagster pipeline locally

To run Dagster pipeline locally make sure the virtual environment is active and then run:

```bash
dagster dev
```

## GCP connection #TODO: needs to be checked physically

Integrating Dagster with GCP enables you to utilise services such as **GCS** and **BigQuery**.

### GCP connection Prerequisites

- A Google Cloud account and a configured GCP project.
- The Google Cloud SDK installed and authenticated on your machine.

### Install dependencies

To integrate with GCP and establish a connection, install the `dagster-gcp` package:

```bash
uv add dagster-gcp
```

### Authentication (local development)

Dagster relies on standard Google authentication. You can authenticate in one of the following ways:

- **Personal login** (writes an `application_default_credentials.json` locally):

  ```bash
  gcloud auth application-default login
  ```

- **Service account JSON** (recommended for automation):

  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service_account.json"
  ```

  (This can also be stored in an `.env` file and loaded via a secrets manager or environment loader.)

### Define resources

In terms of GCP connections, **Dagster offers a simplified approach** through a set of **predefined resource classes** for connecting to services such as **Google Cloud Storage (GCS)** or **BigQuery**.
These resources can be easily added to your project’s definitions:

```python
import dagster as dg
from dagster_gcp.gcs import GCSResource
from dagster_gcp.bigquery import BigQueryResource

from .defs.assets import my_gcs_asset

defs = dg.Definitions(
    assets=[my_gcs_asset],
    resources={
        "gcs": GCSResource(project="my-gcp-project"),
        "bigquery": BigQueryResource(project="my-gcp-project"),
    },
)
```

For more complex projects, resources can be defined separately in a module such as `src/your_project_name/defs/resources.py`.
For example resources are define in `resource.py`:

```python
from dagster_gcp.gcs import GCSResource
from dagster_gcp.bigquery import BigQueryResource

gcs_resource = GCSResource(project="my-gcp-project")
bigquery_resource = BigQueryResource(project="my-gcp-project")
```

then in `definitions.py`

```python
import dagster as dg
from .defs.resources import bigquery_resource, gcs_resource

from .defs.assets import my_gcs_asset

defs = dg.Definitions(
    assets=[my_gcs_asset],
    resources={"gcs": gcs_resource, "bigquery": bigquery_resource},
)
```

- Example of Asset Flow (GCS → BigQuery)

```python
# defs/assets/pipeline.py
from dagster import asset
import pandas as pd
from io import StringIO


@asset(required_resource_keys={"gcs"})
def raw_csv_from_gcs(context):
    client = context.resources.gcs.get_client()
    bucket = client.bucket(context.resources.gcs.bucket)
    blob = bucket.blob("data/input.csv")
    return blob.download_as_text()


@asset(required_resource_keys={"bigquery"})
def load_to_bigquery(context, raw_csv_from_gcs):
    df = pd.read_csv(StringIO(raw_csv_from_gcs))
    client = context.resources.bigquery.get_client()
    table_id = "my_dataset.my_table"
    job = client.load_table_from_dataframe(df, table_id)
    job.result()
    context.log.info(f"Loaded {len(df)} rows into {table_id}")
    return table_id
```

Flow:
**GCS bucket → `raw_csv_from_gcs` asset → `load_to_bigquery` asset → BigQuery table**

Reference for further reading:

- [Installation `uv docs`](https://docs.astral.sh/uv/getting-started/installation/).
- [Creating a New Project `Dagster docs`](https://docs.dagster.io/guides/build/projects/creating-a-new-project)
- [Working on Projects `uv docs`](https://docs.astral.sh/uv/guides/projects/#working-on-projects)
- [Update Project Structure `Dagster docs`](https://docs.dagster.io/guides/build/projects/moving-to-components/migrating-project#step-3-update-project-structure)
- [How to manage dependencies for `uv managed environment`.](https://docs.astral.sh/uv/guides/projects/#managing-dependencies)
- [concepts](https://docs.dagster.io/getting-started/concepts)
- [Dagster Definitions](https://docs.dagster.io/api/dagster/definitions#dagster.Definitions)
