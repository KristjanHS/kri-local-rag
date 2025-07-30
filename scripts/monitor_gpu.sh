#!/bin/bash

# Source centralized configuration
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Setup logging
SCRIPT_NAME=$(get_script_name "${BASH_SOURCE[0]}")
LOG_FILE=$(get_log_file "$SCRIPT_NAME")
setup_logging "$SCRIPT_NAME"

echo "=== GPU Monitoring Script ==="
echo "Timestamp: $(date)"
echo

log_message "INFO" "Checking overall GPU status" | tee -a "$LOG_FILE"
echo "=== Overall GPU Status ==="
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader 2>&1 | tee -a "$LOG_FILE"

echo
log_message "INFO" "Checking container activity" | tee -a "$LOG_FILE"
echo "=== Container Activity ==="

# Check container resource usage
echo "Container CPU/Memory Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>&1 | tee -a "$LOG_FILE"

echo "=== gpustat Output ==="
gpustat 2>&1 | tee -a "$LOG_FILE"

log_message "INFO" "GPU monitoring script completed" | tee -a "$LOG_FILE" 