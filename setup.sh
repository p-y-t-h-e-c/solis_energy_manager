#!/usr/bin/env bash
set -o pipefail

# -----------------------------------------------------------------------------
# ⚙️ Configuration
# -----------------------------------------------------------------------------

# 🎨 Colors
NC='\033[0m'        # No Color
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
MAGENTA='\033[0;35m'

# 🌱 Default virtual environment directory
VENV_DIR=".venv"

# -----------------------------------------------------------------------------
# 🎯 Logging Functions
# -----------------------------------------------------------------------------
print_info()  { echo -e " 💡 [${CYAN}INFO${NC}]   ${CYAN}$1${NC}"; }
print_task()  { echo -e " ⚡ [${YELLOW}TASK${NC}]   ${YELLOW}$1${NC}"; }
print_pass()  { echo -e " ✅ [${GREEN}PASS${NC}]   ${GREEN}$1${NC}"; }
print_warn()  { echo -e " ⚠️ [${MAGENTA}WARN${NC}]   ${MAGENTA}$1${NC}"; }
print_error() { echo -e " ❌ [${RED}FAIL${NC}]   ${RED}$1${NC}"; }

# -----------------------------------------------------------------------------
# 🔍 Virtual Environment Check
# -----------------------------------------------------------------------------
virtual_environment_check() {
  print_info "Checking virtual environment status..."

  if [[ -d "${VENV_DIR}" && -f "${VENV_DIR}/bin/activate" ]]; then
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
      print_pass "Virtual environment found and active."
    else
      print_info "Virtual environment found but not active."
      print_task "Activating..."
      source "${VENV_DIR}/bin/activate"
    fi
  else
    print_warn "No virtual environment found."
    print_task "It will be created during dependency sync..."
  fi

  print_task "Locking and syncing dependencies..."
  uv lock --upgrade
  uv sync --all-groups --all-extras

  if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    print_task "Activating newly created virtual environment..."
    source "${VENV_DIR}/bin/activate"
  fi
}

# -----------------------------------------------------------------------------
# 📦 Version Utilities
# -----------------------------------------------------------------------------
get_current_uv_version() {
  uv --version 2>/dev/null \
    | grep -Eo '[0-9]+(\.[0-9]+){1,2}' \
    | head -n1
}

get_current_pre_commit_version() {
  uv pip show pre-commit 2>/dev/null | awk '$1=="Version:" {print $2}'
}

get_latest_pre_commit_version() {
  uv pip list --outdated 2>/dev/null | awk '$1=="pre-commit" {print $3}'
}


# -----------------------------------------------------------------------------
# 📦 uv Version Management
# -----------------------------------------------------------------------------
uv_status_check() {
  print_info "Checking uv version..."

  local before after update_output
  before="$(get_current_uv_version)"
  print_info "Current version: ${before:-unknown}"

  print_task "Checking for uv updates..."
  if ! update_output="$(uv self update 2>&1)"; then
    print_warn "uv self-update is unavailable (uv may not be a standalone install) — skipping."
    print_warn "${update_output}"
    return 0
  fi

  after="$(get_current_uv_version)"

  if [[ "${before}" == "${after}" ]]; then
    print_pass "uv is already up to date (v${after:-unknown})."
  else
    print_pass "uv upgraded from v${before:-unknown} to v${after:-unknown}."
  fi
  print_info "${update_output}"
}


# -----------------------------------------------------------------------------
# 🔧 pre-commit Management
# -----------------------------------------------------------------------------
pre_commit_status_check() {
  print_info "Checking pre-commit installation ..."

  local current_version latest_version

  current_version="$(get_current_pre_commit_version)"

  if [[ -z "${current_version}" ]]; then
    print_warn "pre-commit is missing."
    print_task "Installing..."
    uv add --dev pre-commit
    current_version="$(get_current_pre_commit_version)"

    if [[ -z "${current_version}" ]]; then
      print_error "There was a problem installing the pre-commit package."
      return 1
    fi
    print_pass "pre-commit installed (v${current_version})."
  else
    print_pass "pre-commit is installed (v${current_version})."
  fi

  print_info "Checking pre-commit version ..."
  latest_version="$(get_latest_pre_commit_version)"

  if [[ -z "${latest_version}" ]]; then
    print_pass "pre-commit is up to date (v${current_version})."
    return 0
  fi

  print_warn "pre-commit is outdated (Current: ${current_version} → Latest: ${latest_version})"
  print_task "Updating..."
  uv lock --upgrade-package pre-commit
  uv sync --all-groups --all-extras

  current_version="$(get_current_pre_commit_version)"
  if [[ "${current_version}" == "${latest_version}" ]]; then
    print_pass "pre-commit updated to v${latest_version}."
  else
    print_warn "There was a problem updating pre-commit, please check pyproject.toml versioning setup."
  fi
}

# -----------------------------------------------------------------------------
# 📄 Config File Creation
# -----------------------------------------------------------------------------
pre_commit_config_create() {
  cat <<EOF > .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: check-added-large-files
      - id: check-docstring-first
      - id: check-yaml
      - id: detect-private-key
      - id: end-of-file-fixer
      - id: no-commit-to-branch
        args: ["--branch", "main"]
      - id: trailing-whitespace

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.12.1
    hooks:
      # Run the linter.
      - id: ruff
        args: [ --fix ]
      # Run the formatter.
      - id: ruff-format

  - repo: https://github.com/astral-sh/uv-pre-commit
    # uv version.
    rev: 0.7.18
    hooks:
      # Update the uv lockfile
      - id: uv-lock

  - repo: https://github.com/tcort/markdown-link-check
    rev: v3.13.7
    hooks:
      - id: markdown-link-check
        args: [-q]

  - repo: https://github.com/igorshubovych/markdownlint-cli
    rev: v0.45.0
    hooks:
    - id: markdownlint
      args: ["--ignore", "CHANGELOG.md", "--fix"]
EOF
}

markdownlint_create() {
  cat <<EOF > .markdownlint.json
{
  "comment": "Markdown Lint Rules",
  "default": true,
  "MD007": {"indent": 4},
  "MD013": false,
  "MD024": false,
  "MD025": {"front_matter_title": ""},
  "MD029": {"style": "one_or_ordered"},
  "MD033": false
}
EOF
}

commitlintrc_create() {
  cat <<EOF > .commitlintrc.json
{
  "rules": {
    "body-leading-blank": [1, "always"],
    "footer-leading-blank": [1, "always"],
    "header-max-length": [2, "always", 72],
    "scope-case": [2, "always", "upper-case"],
    "scope-empty": [2, "never"],
    "subject-case": [2, "never", ["start-case", "pascal-case", "upper-case"]],
    "subject-empty": [2, "never"],
    "subject-full-stop": [2, "never", "."],
    "type-case": [2, "always", "lower-case"],
    "type-empty": [2, "never"],
    "type-enum": [2, "always", ["build","chore","ci","docs","feat","fix","perf","refactor","revert","style","test"]]
  }
}
EOF
}

# -----------------------------------------------------------------------------
# 🔧 Config File Checks
# -----------------------------------------------------------------------------
commitlintrc_file_check() {
  print_info "Checking .commitlintrc.json ..."
  if [[ -f ".commitlintrc.json" ]]; then
    print_pass ".commitlintrc.json already exists, please ensure it has the correct format."
  else
    print_warn ".commitlintrc.json is missing."
    print_task "Creating..."
    commitlintrc_create
    print_pass ".commitlintrc.json created."
  fi
}

markdownlint_file_check() {
  print_info "Checking .markdownlint.json ..."
  if [[ -f ".markdownlint.json" ]]; then
    print_pass ".markdownlint.json already exists, please ensure it has the correct format."
  else
    print_warn ".markdownlint.json is missing."
    print_task "Creating..."
    markdownlint_create
    print_pass ".markdownlint.json created."
  fi
}

# -----------------------------------------------------------------------------
# 🔧 Pre-commit Hooks Check
# -----------------------------------------------------------------------------
commitlint_hook_check() {
  if grep -v '^[[:space:]]*#' .pre-commit-config.yaml | grep -Eq "commit-msg|commitlint"; then
    print_task "Installing commit-msg hook..."
    pre-commit install --hook-type commit-msg
    commitlintrc_file_check
  fi
}

pre_commit_hooks_check() {
  print_info "Checking pre-commit hooks ..."
  if [[ -f ".pre-commit-config.yaml" ]]; then
    print_pass ".pre-commit-config.yaml already exists, please ensure it has the correct format."
    print_task "Updating and installing hooks ..."
    pre-commit autoupdate
    pre-commit install
    commitlint_hook_check
  else
    print_warn ".pre-commit-config.yaml is missing."
    print_task "Creating..."
    pre_commit_config_create
    print_pass ".pre-commit-config.yaml created."
    print_task "Updating hook versions..."
    pre-commit autoupdate
    print_task "Installing hooks..."
    pre-commit install
    commitlint_hook_check
  fi
}

# -----------------------------------------------------------------------------
# 🚀 Execution Flow
# -----------------------------------------------------------------------------
virtual_environment_check || return 1
uv_status_check            || return 1
pre_commit_status_check    || return 1
pre_commit_hooks_check     || return 1
markdownlint_file_check    || return 1

print_pass "🎉 Setup Completed Successfully!"
