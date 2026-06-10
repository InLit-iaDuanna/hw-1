#!/bin/bash
# Raspberry Pi Startup Script for hw-1 Gait Training Controller
# Place in /home/pi/hw1_controller/startup_script.sh
# Make executable: chmod +x startup_script.sh
# Add to crontab: @reboot /home/pi/hw1_controller/startup_script.sh

set -e

# Configuration
PROJECT_DIR="/home/pi/hw1_controller"
PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python3"
MAIN_SCRIPT="${PROJECT_DIR}/src/main_hardware.py"
LOG_DIR="${PROJECT_DIR}/logs"
PID_FILE="${PROJECT_DIR}/controller.pid"

# Logging
STARTUP_LOG="${LOG_DIR}/startup.log"
RUNTIME_LOG="${LOG_DIR}/runtime.log"

# Create log directory
mkdir -p "${LOG_DIR}"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${STARTUP_LOG}"
}

log "=== hw-1 Controller Startup ==="

# Wait for system to stabilize (network, hardware initialization)
log "Waiting 10 seconds for system stabilization..."
sleep 10

# Check if already running
if [ -f "${PID_FILE}" ]; then
    OLD_PID=$(cat "${PID_FILE}")
    if ps -p "${OLD_PID}" > /dev/null 2>&1; then
        log "ERROR: Controller already running with PID ${OLD_PID}"
        exit 1
    else
        log "Removing stale PID file"
        rm -f "${PID_FILE}"
    fi
fi

# Verify Python environment
if [ ! -f "${PYTHON_BIN}" ]; then
    log "ERROR: Python virtual environment not found at ${PYTHON_BIN}"
    exit 1
fi

# Verify main script exists
if [ ! -f "${MAIN_SCRIPT}" ]; then
    log "ERROR: Main script not found at ${MAIN_SCRIPT}"
    exit 1
fi

# Set CPU governor to performance mode for consistent timing
log "Setting CPU governor to performance mode..."
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1 || log "WARNING: Could not set CPU governor"

# Disable power management on USB (prevent IMU disconnection)
log "Disabling USB power management..."
for usb in /sys/bus/usb/devices/*/power/autosuspend; do
    if [ -f "$usb" ]; then
        echo -1 | sudo tee "$usb" > /dev/null 2>&1
    fi
done

# Set nice priority (lower value = higher priority, range: -20 to 19)
NICE_PRIORITY=-10

# Set real-time scheduling policy
# SCHED_FIFO priority range: 1-99 (higher = more priority)
RT_PRIORITY=50

log "Starting controller with real-time priority..."
log "Python: ${PYTHON_BIN}"
log "Script: ${MAIN_SCRIPT}"
log "Nice: ${NICE_PRIORITY}, RT Priority: ${RT_PRIORITY}"

# Start the controller with real-time priority
# Use chrt for real-time scheduling (SCHED_FIFO)
sudo nice -n "${NICE_PRIORITY}" chrt -f "${RT_PRIORITY}" \
    "${PYTHON_BIN}" "${MAIN_SCRIPT}" \
    >> "${RUNTIME_LOG}" 2>&1 &

CONTROLLER_PID=$!

# Save PID
echo "${CONTROLLER_PID}" > "${PID_FILE}"

log "Controller started with PID: ${CONTROLLER_PID}"

# Verify process is running
sleep 2
if ps -p "${CONTROLLER_PID}" > /dev/null 2>&1; then
    log "Controller running successfully"

    # Display process priority info
    SCHED_INFO=$(chrt -p "${CONTROLLER_PID}" 2>/dev/null || echo "Could not retrieve scheduling info")
    log "Scheduling info: ${SCHED_INFO}"

    log "=== Startup Complete ==="
else
    log "ERROR: Controller process died immediately after start"
    rm -f "${PID_FILE}"
    log "Check ${RUNTIME_LOG} for details"
    exit 1
fi

# Optional: Set up watchdog (requires main script to touch watchdog file periodically)
# WATCHDOG_FILE="${PROJECT_DIR}/watchdog.txt"
# (while true; do
#     if [ -f "${PID_FILE}" ]; then
#         CURRENT_PID=$(cat "${PID_FILE}")
#         if ps -p "${CURRENT_PID}" > /dev/null 2>&1; then
#             # Check if watchdog file was updated in last 30 seconds
#             if [ -f "${WATCHDOG_FILE}" ]; then
#                 AGE=$(($(date +%s) - $(stat -c %Y "${WATCHDOG_FILE}")))
#                 if [ ${AGE} -gt 30 ]; then
#                     log "WATCHDOG: Process frozen, restarting..."
#                     kill -9 "${CURRENT_PID}"
#                     rm -f "${PID_FILE}"
#                     exec "$0"  # Restart this script
#                 fi
#             fi
#         else
#             log "WATCHDOG: Process died, restarting..."
#             rm -f "${PID_FILE}"
#             exec "$0"  # Restart this script
#         fi
#     fi
#     sleep 10
# done) &

exit 0
