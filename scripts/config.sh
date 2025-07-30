#!/bin/bash
# Centralized configuration for all shell scripts
# This file defines all important paths and can be sourced by other scripts

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

# Global logging function
log_message() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message"
}

# Function to get log file path for a script
get_log_file() {
    local script_name="$1"
    local log_file="$LOGS_DIR/${script_name}.log"
    
    # Ensure logs directory exists
    mkdir -p "$LOGS_DIR"
    
    # Return the log file path
    echo "$log_file"
}

# Function to setup logging for shell scripts
setup_logging() {
    local script_name="$1"
    local log_file="$LOGS_DIR/${script_name}.log"
    
    # Ensure logs directory exists
    mkdir -p "$LOGS_DIR"
    
    # Log script start
    log_message "INFO" "Starting $script_name" | tee -a "$log_file"
}

# Function to get script name without extension
get_script_name() {
    local script_path="$1"
    basename "$script_path" .sh
}

# Validate directories on source
validate_directories 