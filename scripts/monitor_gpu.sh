#!/bin/bash

echo "=== GPU Monitoring Script ==="
echo "Timestamp: $(date)"
echo

echo "=== Overall GPU Status ==="
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader

echo
echo "=== Container Activity ==="

# Check container resource usage
echo "Container CPU/Memory Usage:"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

echo "=== gpustat Output ==="
gpustat 