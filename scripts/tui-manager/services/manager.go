package services

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode"

	"apicortex-manager/config"
)

type ServiceStatus int

const (
	StatusStopped ServiceStatus = iota
	StatusStarting
	StatusRunning
	StatusError
	StatusStopping
)

func (s ServiceStatus) String() string {
	switch s {
	case StatusStopped:
		return "Stopped"
	case StatusStarting:
		return "Starting"
	case StatusRunning:
		return "Running"
	case StatusError:
		return "Error"
	case StatusStopping:
		return "Stopping"
	default:
		return "Unknown"
	}
}

type LogLine struct {
	Timestamp time.Time
	Service   string
	Level     string
	Message   string
	Raw       string
}

type ServiceInstance struct {
	Name      string
	Config    *config.ServiceConfig
	Status    ServiceStatus
	LogBuffer []LogLine
	LogMutex  sync.Mutex
	cmd       *exec.Cmd
	lastError error
	startTime time.Time
	Health    bool
	exitChan  chan error
	jobHandle uintptr
}

type Manager struct {
	config   *config.Config
	services map[string]*ServiceInstance
	mu       sync.RWMutex
}

func NewManager(cfg *config.Config) *Manager {
	return &Manager{
		config:   cfg,
		services: make(map[string]*ServiceInstance),
	}
}

func (m *Manager) StartService(name string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	svcConfig, ok := m.config.GetService(name)
	if !ok {
		return fmt.Errorf("service %s not found in config", name)
	}

	if name == "cloudflared" {
		if err := ensureDockerAvailable(); err != nil {
			instance := &ServiceInstance{
				Name:      svcConfig.Name,
				Config:    svcConfig,
				Status:    StatusError,
				LogBuffer: make([]LogLine, 0, 1000),
				Health:    false,
				lastError: err,
			}
			instance.sendLog("ERROR", fmt.Sprintf("Docker unavailable: %v", err))
			m.services[name] = instance
			return fmt.Errorf("cloudflared requires docker: %w", err)
		}
	}

	if existing, ok := m.services[name]; ok {
		if existing.Status == StatusRunning || existing.Status == StatusStarting {
			return fmt.Errorf("service %s is already active", name)
		}
	}

	// Create instance first so we can log port operations
	instance := &ServiceInstance{
		Name:      svcConfig.Name,
		Config:    svcConfig,
		Status:    StatusStarting,
		LogBuffer: make([]LogLine, 0, 1000),
		Health:    false,
	}
	m.services[name] = instance

	// Check and free port before starting
	port := svcConfig.Port
	if port > 0 {
		// First attempt to kill any process on the port
		if !IsPortAvailable(port) {
			instance.sendLog("INFO", fmt.Sprintf("Port %d is in use, attempting to free...", port))
			if err := KillProcessOnPort(port); err != nil {
				instance.sendLog("WARN", fmt.Sprintf("Could not kill process on port %d: %v", port, err))
			}
			// Wait for port to become available
			if waitErr := WaitForPortAvailable(port, 5*time.Second); waitErr != nil {
				instance.Status = StatusError
				instance.sendLog("ERROR", fmt.Sprintf("Port %d is still in use after cleanup attempts", port))
				return fmt.Errorf("port %d unavailable: %w", port, waitErr)
			}
		}
		// Additional safety delay to ensure OS has released the port
		time.Sleep(500 * time.Millisecond)
		
		// Final verification
		if !IsPortAvailable(port) {
			instance.Status = StatusError
			instance.sendLog("ERROR", fmt.Sprintf("Port %d is still in use after verification", port))
			return fmt.Errorf("port %d still in use", port)
		}
		instance.sendLog("INFO", fmt.Sprintf("Port %d verified available", port))
	}

	m.services[name] = instance

	go instance.run(m.config)

	return nil
}

func (m *Manager) StopService(name string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	instance, ok := m.services[name]
	if !ok {
		return fmt.Errorf("service %s not found", name)
	}

	instance.Status = StatusStopping

	if name == "cloudflared" {
		go m.stopCloudflared(instance)
		return nil
	}

	if instance.cmd != nil && instance.cmd.Process != nil {
		pid := instance.cmd.Process.Pid
		port := instance.Config.Port
		
		// First, try to kill any process on the port (in case it's a child process)
		if port > 0 {
			instance.sendLog("INFO", fmt.Sprintf("Releasing port %d...", port))
			_ = KillProcessOnPort(port)
			time.Sleep(300 * time.Millisecond)
		}
		
		// Force kill the main process tree immediately
		if err := killProcessTree(pid); err != nil {
			instance.sendLog("WARN", fmt.Sprintf("Failed to kill process tree: %v", err))
		}
		
		// Wait for exit channel with timeout
		if instance.exitChan != nil {
			select {
			case <-instance.exitChan:
				instance.sendLog("INFO", "Process exited")
			case <-time.After(2 * time.Second):
				instance.sendLog("WARN", "Process did not exit in time, forcing kill")
				_ = killProcessTree(pid)
			}
		}
		
		// Additional wait for port release
		if port > 0 {
			instance.sendLog("INFO", fmt.Sprintf("Waiting for port %d to be released...", port))
			if err := WaitForPortAvailable(port, 5*time.Second); err != nil {
				instance.sendLog("WARN", fmt.Sprintf("Port %d may still be in use: %v", port, err))
				// One more aggressive kill attempt
				_ = KillProcessOnPort(port)
				time.Sleep(1 * time.Second)
			} else {
				instance.sendLog("INFO", fmt.Sprintf("Port %d is now available", port))
			}
		}
		
		instance.Status = StatusStopped
		instance.Health = false
	} else {
		instance.Status = StatusStopped
		instance.Health = false
	}

	return nil
}

func (m *Manager) stopCloudflared(instance *ServiceInstance) {
	workDir := m.config.ResolveWorkingDir(instance.Config.WorkingDir)
	ctx, cancel := context.WithTimeout(context.Background(), 25*time.Second)
	defer cancel()

	downCmd := exec.CommandContext(ctx, "docker", "compose", "down", "--remove-orphans")
	downCmd.Dir = workDir
	downOutput, downErr := downCmd.CombinedOutput()
	m.logCommandOutput(instance, "[COMPOSE DOWN]", downOutput)

	if downErr != nil {
		if ctx.Err() == context.DeadlineExceeded {
			instance.sendLog("ERROR", "docker compose down timed out")
		} else {
			instance.sendLog("ERROR", fmt.Sprintf("docker compose down failed: %v", downErr))
		}
		instance.lastError = downErr
	}

	if instance.cmd != nil && instance.cmd.Process != nil {
		pid := instance.cmd.Process.Pid
		_ = instance.cmd.Process.Signal(os.Interrupt)
		m.waitForExitOrKill(instance, pid, 2*time.Second)
		return
	}

	if downErr != nil {
		instance.Status = StatusError
		instance.Health = false
		return
	}

	instance.Status = StatusStopped
	instance.Health = false
}

func (m *Manager) waitForExitOrKill(inst *ServiceInstance, pid int, timeout time.Duration) {
	exited := false
	if inst.exitChan != nil {
		select {
		case err := <-inst.exitChan:
			if err != nil {
				inst.sendLog("WARN", fmt.Sprintf("Service PID %d exited with error: %v", pid, err))
			} else {
				inst.sendLog("INFO", fmt.Sprintf("Service PID %d exited gracefully", pid))
			}
			exited = true
		case <-time.After(timeout):
		}
	} else {
		time.Sleep(timeout)
	}

	if exited {
		m.cleanupJobHandle(inst)
		return
	}

	if err := killProcessTree(pid); err != nil {
		inst.sendLog("ERROR", fmt.Sprintf("Failed to force-kill PID %d: %v", pid, err))
	} else {
		inst.sendLog("INFO", fmt.Sprintf("Force-killed PID %d", pid))
	}

	m.cleanupJobHandle(inst)
}

func (m *Manager) cleanupJobHandle(inst *ServiceInstance) {
	if inst.jobHandle == 0 {
		return
	}
	if err := closeJob(inst.jobHandle); err != nil {
		inst.sendLog("DEBUG", fmt.Sprintf("Failed to close job handle 0x%x: %v", inst.jobHandle, err))
	} else {
		inst.sendLog("DEBUG", fmt.Sprintf("Closed job handle 0x%x", inst.jobHandle))
	}
	inst.jobHandle = 0
}

func (m *Manager) logCommandOutput(inst *ServiceInstance, prefix string, output []byte) {
	if len(output) == 0 {
		return
	}
	scanner := bufio.NewScanner(strings.NewReader(string(output)))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		level := detectLogLevel(line)
		inst.sendLog(level, fmt.Sprintf("%s %s", prefix, line))
	}
}

func (m *Manager) StopAll() {
	m.mu.RLock()
	names := make([]string, 0)
	for name := range m.services {
		names = append(names, name)
	}
	m.mu.RUnlock()

	for _, name := range names {
		m.StopService(name)
	}
}

func (m *Manager) GetService(name string) (*ServiceInstance, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	svc, ok := m.services[name]
	return svc, ok
}

func (s *ServiceInstance) GetLogs(count int) []LogLine {
	s.LogMutex.Lock()
	defer s.LogMutex.Unlock()

	if len(s.LogBuffer) == 0 {
		return []LogLine{}
	}

	start := len(s.LogBuffer) - count
	if start < 0 {
		start = 0
	}

	result := make([]LogLine, len(s.LogBuffer[start:]))
	copy(result, s.LogBuffer[start:])
	return result
}

func (s *ServiceInstance) run(cfg *config.Config) {
	s.startTime = time.Now()
	s.Status = StatusStarting

	workDir := cfg.ResolveWorkingDir(s.Config.WorkingDir)
	if _, err := os.Stat(workDir); err != nil {
		s.sendLog("ERROR", fmt.Sprintf("Working directory missing: %s (%v)", workDir, err))
		s.Status = StatusError
		s.Health = false
		s.lastError = err
		return
	}

	commandPath := s.Config.Command
	if !filepath.IsAbs(commandPath) && (strings.Contains(commandPath, string(os.PathSeparator)) || strings.Contains(commandPath, "/")) {
		commandPath = filepath.Clean(filepath.Join(cfg.ConfigDir, commandPath))
	}

	cmd := exec.Command(commandPath, s.Config.Args...)
	cmd.Dir = workDir

	setProcessGroup(cmd)

	env := os.Environ()
	for k, v := range s.Config.Env {
		env = addEnv(env, k, v)
	}
	cmd.Env = env

	if err := s.runPreStartCommands(cfg, workDir, env); err != nil {
		s.sendLog("ERROR", fmt.Sprintf("Pre-start failed: %v", err))
		s.Status = StatusError
		s.Health = false
		s.lastError = err
		return
	}

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		s.sendLog("ERROR", fmt.Sprintf("Failed to create stdout pipe: %v", err))
		s.Status = StatusError
		s.lastError = err
		return
	}

	stderr, err := cmd.StderrPipe()
	if err != nil {
		s.sendLog("ERROR", fmt.Sprintf("Failed to create stderr pipe: %v", err))
		s.Status = StatusError
		s.lastError = err
		return
	}

	if err := cmd.Start(); err != nil {
		s.sendLog("ERROR", fmt.Sprintf("Failed to start service: %v", err))
		s.Status = StatusError
		s.lastError = err
		return
	}

	s.cmd = cmd

	s.exitChan = make(chan error, 1)

	if h, err := assignProcessToJob(s.cmd.Process.Pid); err == nil && h != 0 {
		s.jobHandle = h
		s.sendLog("DEBUG", fmt.Sprintf("Assigned PID %d to job handle 0x%x", s.cmd.Process.Pid, h))
	} else if err != nil {
		s.sendLog("DEBUG", fmt.Sprintf("Job assignment not available: %v", err))
	}

	s.Status = StatusRunning
	s.sendLog("INFO", fmt.Sprintf("Service started successfully (PID: %d)", s.cmd.Process.Pid))
	s.Health = true

	done := make(chan error, 2)

	go func() {
		s.readLogs(stdout, "STDOUT")
		done <- nil
	}()

	go func() {
		s.readLogs(stderr, "STDERR")
		done <- nil
	}()

	<-done
	<-done

	err = s.cmd.Wait()
	if s.exitChan != nil {
		s.exitChan <- err
		close(s.exitChan)
	}
	if err != nil {
		s.sendLog("ERROR", fmt.Sprintf("Process exited with error: %v", err))
		s.Status = StatusError
		s.Health = false
		s.lastError = err
	} else {
		s.Status = StatusStopped
		s.Health = false
	}
}

func (s *ServiceInstance) readLogs(reader io.Reader, prefix string) {
	scanner := bufio.NewScanner(reader)
	for scanner.Scan() {
		line := scanner.Text()
		if line != "" {
			level := detectLogLevel(line)
			s.sendLog(level, fmt.Sprintf("[%s] %s", prefix, line))
		}
	}
}

func (s *ServiceInstance) sendLog(level, message string) {
	line := LogLine{
		Timestamp: time.Now(),
		Service:   s.Name,
		Level:     level,
		Message:   message,
		Raw: fmt.Sprintf("[%s] %s %s",
			time.Now().Format("15:04:05"),
			level,
			message),
	}

	s.LogMutex.Lock()
	defer s.LogMutex.Unlock()

	s.LogBuffer = append(s.LogBuffer, line)
	if len(s.LogBuffer) > 5000 {
		s.LogBuffer = s.LogBuffer[len(s.LogBuffer)-5000:]
	}
}

func detectLogLevel(line string) string {
	trimmed := strings.TrimSpace(line)
	if strings.HasPrefix(trimmed, "{") {
		var payload struct {
			Level string `json:"level"`
		}
		if err := json.Unmarshal([]byte(trimmed), &payload); err == nil {
			switch strings.ToUpper(strings.TrimSpace(payload.Level)) {
			case "ERROR", "CRITICAL", "FATAL", "PANIC":
				return "ERROR"
			case "WARN", "WARNING":
				return "WARN"
			case "INFO":
				return "INFO"
			case "DEBUG", "TRACE":
				return "DEBUG"
			}
		}
	}

	lower := strings.ToLower(trimmed)
	words := strings.FieldsFunc(lower, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
	hasWord := func(target string) bool {
		for _, word := range words {
			if word == target {
				return true
			}
		}
		return false
	}

	if hasWord("error") || hasWord("fatal") || hasWord("panic") {
		return "ERROR"
	}
	if hasWord("warn") || hasWord("warning") {
		return "WARN"
	}
	if hasWord("info") || hasWord("started") || hasWord("listening") {
		return "INFO"
	}
	return "DEBUG"
}

func addEnv(env []string, key, value string) []string {

	prefix := key + "="
	filtered := make([]string, 0)
	for _, e := range env {
		if !strings.HasPrefix(e, prefix) {
			filtered = append(filtered, e)
		}
	}

	return append(filtered, key+"="+value)
}

func (s *ServiceInstance) runPreStartCommands(cfg *config.Config, workDir string, env []string) error {
	if len(s.Config.PreStart) == 0 {
		return nil
	}

	for idx, step := range s.Config.PreStart {
		command := strings.TrimSpace(step.Command)
		if command == "" {
			return fmt.Errorf("pre_start step %d has empty command", idx+1)
		}
		if !filepath.IsAbs(command) && (strings.Contains(command, string(os.PathSeparator)) || strings.Contains(command, "/")) {
			command = filepath.Clean(filepath.Join(cfg.ConfigDir, command))
		}

		s.sendLog("INFO", fmt.Sprintf("Running pre-start step %d/%d: %s %s", idx+1, len(s.Config.PreStart), command, strings.Join(step.Args, " ")))
		preCmd := exec.Command(command, step.Args...)
		preCmd.Dir = workDir
		preCmd.Env = env
		output, err := preCmd.CombinedOutput()
		if len(output) > 0 {
			scanner := bufio.NewScanner(strings.NewReader(string(output)))
			for scanner.Scan() {
				line := strings.TrimSpace(scanner.Text())
				if line == "" {
					continue
				}
				level := detectLogLevel(line)
				s.sendLog(level, fmt.Sprintf("[PRESTART] %s", line))
			}
		}
		if err != nil {
			return fmt.Errorf("pre_start step %d failed: %w", idx+1, err)
		}
	}

	return nil
}

func ensureDockerAvailable() error {
	if _, err := exec.LookPath("docker"); err != nil {
		return fmt.Errorf("docker executable not found in PATH")
	}

	ctxInfo, cancelInfo := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancelInfo()
	infoOut, infoErr := exec.CommandContext(ctxInfo, "docker", "info", "--format", "{{.ServerVersion}}").CombinedOutput()
	if infoErr != nil {
		message := strings.TrimSpace(string(infoOut))
		if message == "" {
			message = infoErr.Error()
		}
		return fmt.Errorf("docker daemon unavailable: %s", message)
	}

	ctxCompose, cancelCompose := context.WithTimeout(context.Background(), 8*time.Second)
	defer cancelCompose()
	composeOut, composeErr := exec.CommandContext(ctxCompose, "docker", "compose", "version").CombinedOutput()
	if composeErr != nil {
		message := strings.TrimSpace(string(composeOut))
		if message == "" {
			message = composeErr.Error()
		}
		return fmt.Errorf("docker compose unavailable: %s", message)
	}

	return nil
}

func CheckDockerAvailability() error {
	return ensureDockerAvailable()
}

func killProcessTree(pid int) error {
	if pid <= 0 {
		return nil
	}
	if runtime.GOOS == "windows" {
		cmd := exec.Command("taskkill", "/T", "/F", "/PID", strconv.Itoa(pid))
		return cmd.Run()
	}

	pgid := fmt.Sprintf("-%d", pid)
	cmd := exec.Command("kill", "-TERM", pgid)
	if err := cmd.Run(); err == nil {
		return nil
	}

	return exec.Command("kill", "-TERM", strconv.Itoa(pid)).Run()
}
