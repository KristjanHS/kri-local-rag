#!/bin/bash
# Centralized configuration for all shell scripts
# This file defines all important paths and common logging utilities.

# Get the project root directory (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Ensure we're in the project root
if [ ! -f "$PROJECT_ROOT/docker/docker-compose.yml" ]; then
    echo "Error: Please run scripts from the project root directory."
    exit 1
fi

# Change to project root for all operations
cd "$PROJECT_ROOT"

# Define all important paths relative to project root
export DOCKER_COMPOSE_FILE="docker/docker-compose.yml"
export BACKEND_DIR="backend"
export DATA_DIR="data"
export LOGS_DIR="logs"
export EXAMPLE_DATA_DIR="example_data"

# Docker service names
export APP_SERVICE="app"
export WEAVIATE_SERVICE="weaviate"
export OLLAMA_SERVICE="ollama"

# Default values that can be overridden by environment variables
export DEFAULT_DATA_PATH="${DEFAULT_DATA_PATH:-$DATA_DIR}"
export DEFAULT_LOG_LEVEL="${DEFAULT_LOG_LEVEL:-INFO}"

# Function to validate that required directories exist
validate_directories() {
    local missing_dirs=()
    
    for dir in "$DATA_DIR" "$LOGS_DIR" "$BACKEND_DIR"; do
        if [ ! -d "$dir" ]; then
            missing_dirs+=("$dir")
        fi
    done
    
    if [ ${#missing_dirs[@]} -gt 0 ]; then
        echo "Warning: The following directories are missing:"
        printf '  %s\n' "${missing_dirs[@]}"
        echo "Creating missing directories..."
        mkdir -p "${missing_dirs[@]}"
    fi
}

# Function to get relative path from project root
get_relative_path() {
    local path="$1"
    if [[ "$path" == /* ]]; then
        # Absolute path - convert to relative
        echo "$(realpath --relative-to="$PROJECT_ROOT" "$path")"
    else
        # Already relative
        echo "$path"
    fi
}

# Function to resolve path relative to project root
resolve_path() {
    local path="$1"
    if [[ "$path" == /* ]]; then
        # Absolute path - return as is
        echo "$path"
    else
        # Relative path - return as is (since we're already in project root)
        echo "$path"
    fi
}

# --------------------------- Logging utilities ------------------------------

# LOG_LEVEL controls verbosity (DEBUG, INFO, WARN, ERROR). Default: INFO
export LOG_LEVEL=${LOG_LEVEL:-INFO}

_log_level_to_num() {
    case "$1" in
        DEBUG) echo 10 ;;
        INFO)  echo 20 ;;
        WARN)  echo 30 ;;
        ERROR) echo 40 ;;
        *)     echo 20 ;;
    esac
}

_LOG_THRESHOLD=$(_log_level_to_num "$LOG_LEVEL")

_is_tty() {
    [ -t 1 ] && echo 1 || echo 0
}

# Print a single log line to stdout with optional color if TTY
log() {
    local level="$1"; shift
    local msg="$*"
    local ts
    ts=$(date -Is)
    local nlevel=$(_log_level_to_num "$level")
    if [ "$nlevel" -lt "$_LOG_THRESHOLD" ]; then
        return 0
    fi
    if [ "$(_is_tty)" -eq 1 ]; then
        case "$level" in
            DEBUG) printf "%s [\033[36m%s\033[0m] %s\n" "$ts" "$level" "$msg" ;;
            INFO)  printf "%s [\033[32m%s\033[0m] %s\n" "$ts" "$level" "$msg" ;;
            WARN)  printf "%s [\033[33m%s\033[0m] %s\n" "$ts" "$level" "$msg" ;;
            ERROR) printf "%s [\033[31m%s\033[0m] %s\n" "$ts" "$level" "$msg" ;;
            *)     printf "%s [%s] %s\n" "$ts" "$level" "$msg" ;;
        esac
    else
        printf "%s [%s] %s\n" "$ts" "$level" "$msg"
    fi
}

# Backwards-compatible helper
log_message() {
    log "$@"
}

# Create a timestamped log file and a stable symlink <name>.log → <name>-<ts>.log
init_script_logging() {
    local script_name="$1"
    mkdir -p "$LOGS_DIR"
    local ts
    ts=$(date +%Y%m%d-%H%M%S)
    local log_file="$LOGS_DIR/${script_name}-${ts}.log"
    ln -sf "$(basename "$log_file")" "$LOGS_DIR/${script_name}.log"
    echo "$log_file"
}

# Error trap: logs failing command and line number to both stdout and log file
enable_error_trap() {
    local log_file="$1"
    local script_name="$2"
    trap 'rc=$?; line=${BASH_LINENO[0]:-?}; cmd=${BASH_COMMAND:-?}; msg="${script_name}: line ${line}: ${cmd} (exit ${rc})"; log ERROR "$msg" | tee -a "$log_file"; exit $rc' ERR
}

# Optional debug trace to the log file only (export DEBUG=1 to enable)
enable_debug_trace() {
    local log_file="$1"
    exec 3>>"$log_file"
    export BASH_XTRACEFD=3
    export PS4='+ $(date -Is) ${BASH_SOURCE##*/}:${LINENO}: '
    if [ "${DEBUG:-}" = "1" ]; then
        set -x
    fi
}

# Run a step with timing and status logging
run_step() {
    local title="$1"; shift
    local log_file="$1"; shift
    local t0=$(date +%s)
    log INFO "▶ ${title}" | tee -a "$log_file"
    if "$@"; then
        local dt=$(( $(date +%s) - t0 ))
        log INFO "✔ ${title} (${dt}s)" | tee -a "$log_file"
    else
        local rc=$?
        log ERROR "✖ ${title} failed (exit ${rc})" | tee -a "$log_file"
        return $rc
    fi
}

# --------------------- Backward-compat logging wrappers ---------------------

# Return the stable symlink path for a script's log
get_log_file() {
    local script_name="$1"
    mkdir -p "$LOGS_DIR"
    echo "$LOGS_DIR/${script_name}.log"
}

# Ensure a timestamped log exists and the symlink points to it, then log start
setup_logging() {
    local script_name="$1"
    local ts_log
    ts_log=$(init_script_logging "$script_name")
    log INFO "Starting $script_name" | tee -a "$ts_log"
}

# ------------------------ Misc. utility functions ---------------------------

# Function to get script name without extension
get_script_name() {
    local script_path="$1"
    basename "$script_path" .sh
}

# Validate directories on source
validate_directories 