#!/bin/bash
set -Eeuo pipefail

# Source centralized configuration
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Setup logging
SCRIPT_NAME=$(get_script_name "${BASH_SOURCE[0]}")
LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
enable_debug_trace "$LOG_FILE"
log INFO "Starting $SCRIPT_NAME" | tee -a "$LOG_FILE"

echo "=== GPU Monitoring Script ==="
echo "Timestamp: $(date)"
echo

log INFO "Checking overall GPU status" | tee -a "$LOG_FILE"
echo "=== Overall GPU Status ==="
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader 2>&1 | tee -a "$LOG_FILE"

echo
log INFO "Checking container activity" | tee -a "$LOG_FILE"
echo "=== Container Activity ==="

# Check container resource usage
echo "Container CPU/Memory Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>&1 | tee -a "$LOG_FILE"

echo "=== gpustat Output ==="
gpustat 2>&1 | tee -a "$LOG_FILE"

log INFO "GPU monitoring script completed" | tee -a "$LOG_FILE"