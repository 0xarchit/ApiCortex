package services

import (
	"fmt"
	"net"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
	"time"
)

// IsPortAvailable checks if a TCP port is available for binding
func IsPortAvailable(port int) bool {
	if port <= 0 {
		return true
	}

	ln, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return false
	}
	ln.Close()
	return true
}

// WaitForPortAvailable waits for a port to become available
func WaitForPortAvailable(port int, timeout time.Duration) error {
	if port <= 0 {
		return nil
	}

	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		if IsPortAvailable(port) {
			return nil
		}
		time.Sleep(200 * time.Millisecond)
	}

	return fmt.Errorf("port %d is still in use after %v", port, timeout)
}

// KillProcessOnPort attempts to kill any process using the specified port
func KillProcessOnPort(port int) error {
	if port <= 0 {
		return nil
	}

	if runtime.GOOS == "windows" {
		return killProcessOnPortWindows(port)
	}
	return killProcessOnPortUnix(port)
}

// ForceReleasePort aggressively kills any process on the port and waits for release
func ForceReleasePort(port int, timeout time.Duration) error {
	if port <= 0 {
		return nil
	}

	// Try to kill process on port
	_ = KillProcessOnPort(port)
	
	// Wait for port to be released
	return WaitForPortAvailable(port, timeout)
}

func killProcessOnPortWindows(port int) error {
	// Find process using the port
	cmd := exec.Command("netstat", "-ano")
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to run netstat: %w", err)
	}

	portStr := fmt.Sprintf(":%d", port)
	lines := strings.Split(string(output), "\n")
	killed := false

	for _, line := range lines {
		// Look for LISTENING or TIME_WAIT or ESTABLISHED
		if strings.Contains(line, portStr) && (strings.Contains(line, "LISTENING") || strings.Contains(line, "TIME_WAIT") || strings.Contains(line, "ESTABLISHED")) {
			// Extract PID (last field)
			fields := strings.Fields(line)
			if len(fields) >= 5 {
				pidStr := fields[len(fields)-1]
				pid, err := strconv.Atoi(pidStr)
				if err == nil && pid > 0 && pid != 0 && pid != 4 {
					// Kill the process tree
					killCmd := exec.Command("taskkill", "/F", "/T", "/PID", strconv.Itoa(pid))
					_ = killCmd.Run()
					killed = true
				}
			}
		}
	}

	if !killed {
		return fmt.Errorf("no process found on port %d", port)
	}
	return nil
}

func killProcessOnPortUnix(port int) error {
	cmd := exec.Command("lsof", "-ti", fmt.Sprintf(":%d", port))
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("no process found on port %d", port)
	}

	pids := strings.Split(strings.TrimSpace(string(output)), "\n")
	for _, pidStr := range pids {
		if pidStr == "" {
			continue
		}
		killCmd := exec.Command("kill", "-9", pidStr)
		_ = killCmd.Run()
	}

	return nil
}
