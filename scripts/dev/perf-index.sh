#!/usr/bin/env bash
# Performance test script for indexer: cold vs warm cache
# Usage: ./scripts/dev/perf-index.sh <test_media_directory>

set -euo pipefail

# Colors for output
COLOR_RESET='\033[0m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_BLUE='\033[0;34m'
COLOR_RED='\033[0;31m'

echo -e "${COLOR_BLUE}=== WomCast Indexer Performance Test ===${COLOR_RESET}"
echo ""

# Validate arguments
if [ $# -lt 1 ]; then
    echo -e "${COLOR_RED}Error: Missing test directory argument${COLOR_RESET}"
    echo "Usage: $0 <test_media_directory>"
    exit 1
fi

TEST_DIR="$1"

# Validate test directory
if [ ! -d "$TEST_DIR" ]; then
    echo -e "${COLOR_RED}Error: Test directory does not exist: $TEST_DIR${COLOR_RESET}"
    exit 1
fi

FILE_COUNT=$(find "$TEST_DIR" -type f | wc -l)
echo -e "${COLOR_YELLOW}Test directory: $TEST_DIR${COLOR_RESET}"
echo -e "${COLOR_YELLOW}Total files: $FILE_COUNT${COLOR_RESET}"
echo ""

# Database path
DB_PATH="womcast.db"
BACKUP_PATH="womcast_backup.db"

# Get Python executable path
PYTHON_EXE="${PYTHON_EXE:-python3}"
if ! command -v "$PYTHON_EXE" &> /dev/null; then
    echo -e "${COLOR_RED}Error: Python executable not found: $PYTHON_EXE${COLOR_RESET}"
    echo -e "${COLOR_YELLOW}Set PYTHON_EXE environment variable or ensure python3 is in PATH${COLOR_RESET}"
    exit 1
fi

# Function to run indexer and measure time
measure_indexer_run() {
    local run_type="$1"
    local test_path="$2"
    
    echo -e "${COLOR_BLUE}--- $run_type Run ---${COLOR_RESET}"
    
    local start_time=$(date +%s.%N)
    $PYTHON_EXE -m backend.metadata.indexer "$test_path"
    local end_time=$(date +%s.%N)
    
    local duration=$(echo "$end_time - $start_time" | bc)
    echo -e "${COLOR_GREEN}$run_type time: ${duration}s${COLOR_RESET}"
    echo ""
    
    echo "$duration"
}

# Backup existing database if present
if [ -f "$DB_PATH" ]; then
    echo -e "${COLOR_YELLOW}Backing up existing database...${COLOR_RESET}"
    cp "$DB_PATH" "$BACKUP_PATH"
fi

# === COLD CACHE TEST ===
echo ""
echo -e "${COLOR_BLUE}=== Cold Cache Test ===${COLOR_RESET}"
echo -e "${COLOR_YELLOW}Removing database and clearing cache...${COLOR_RESET}"
rm -f "$DB_PATH"
sync
sleep 0.5

COLD_TIME=$(measure_indexer_run "Cold" "$TEST_DIR")

# === WARM CACHE TEST ===
echo ""
echo -e "${COLOR_BLUE}=== Warm Cache Test ===${COLOR_RESET}"
echo -e "${COLOR_YELLOW}Running indexer again with warm cache...${COLOR_RESET}"

WARM_TIME=$(measure_indexer_run "Warm" "$TEST_DIR")

# === RESULTS ===
echo ""
echo -e "${COLOR_BLUE}=== Performance Results ===${COLOR_RESET}"
echo "Test directory:     $TEST_DIR"
echo "Total files:        $FILE_COUNT"
echo "Cold cache time:    ${COLD_TIME}s"
echo "Warm cache time:    ${WARM_TIME}s"
echo "Speedup:            $(echo "scale=2; $COLD_TIME / $WARM_TIME" | bc)x"
echo "Cold throughput:    $(echo "scale=1; $FILE_COUNT / $COLD_TIME" | bc) files/s"
echo "Warm throughput:    $(echo "scale=1; $FILE_COUNT / $WARM_TIME" | bc) files/s"

# Check performance thresholds
THRESHOLD=5.0
if [ "$FILE_COUNT" -ge 1000 ]; then
    if (( $(echo "$COLD_TIME > $THRESHOLD" | bc -l) )); then
        echo ""
        echo -e "${COLOR_RED}⚠ Performance Warning: Cold cache exceeded ${THRESHOLD}s threshold for 1000+ files${COLOR_RESET}"
        echo -e "${COLOR_YELLOW}Expected: ≤${THRESHOLD}s for 1k files${COLOR_RESET}"
        echo -e "${COLOR_YELLOW}Actual:   ${COLD_TIME}s${COLOR_RESET}"
        EXIT_CODE=1
    else
        echo ""
        echo -e "${COLOR_GREEN}✓ Performance OK: Cold cache within expected range${COLOR_RESET}"
        EXIT_CODE=0
    fi
else
    echo ""
    echo -e "${COLOR_YELLOW}ℹ Skipping threshold check (requires 1000+ files)${COLOR_RESET}"
    EXIT_CODE=0
fi

# Restore backup if it existed
if [ -f "$BACKUP_PATH" ]; then
    echo ""
    echo -e "${COLOR_YELLOW}Restoring original database...${COLOR_RESET}"
    rm -f "$DB_PATH"
    mv "$BACKUP_PATH" "$DB_PATH"
fi

echo ""
exit $EXIT_CODE
