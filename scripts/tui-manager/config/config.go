package config

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

type CommandConfig struct {
	Command string   `yaml:"command"`
	Args    []string `yaml:"args"`
}

type ServiceConfig struct {
	Name        string            `yaml:"name"`
	Command     string            `yaml:"command"`
	Args        []string          `yaml:"args"`
	PreStart    []CommandConfig   `yaml:"pre_start"`
	WorkingDir  string            `yaml:"working_dir"`
	HealthCheck string            `yaml:"health_check"`
	Port        int               `yaml:"port"`
	Env         map[string]string `yaml:"env"`
}

type Config struct {
	Services    map[string]ServiceConfig `yaml:"services"`
	ConfigDir   string
	ProjectRoot string
}

func LoadConfig() (*Config, error) {

	configPath := findConfigFile()
	if configPath == "" {
		return nil, fmt.Errorf("config.yml not found in standard locations")
	}

	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, fmt.Errorf("reading config: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parsing config: %w", err)
	}

	absConfigPath, err := filepath.Abs(configPath)
	if err != nil {
		absConfigPath = configPath
	}
	cfg.ConfigDir = filepath.Dir(absConfigPath)
	cfg.ProjectRoot = filepath.Clean(filepath.Join(cfg.ConfigDir, "..", ".."))

	return &cfg, nil
}

func findConfigFile() string {

	execPath, err := os.Executable()
	if err == nil {
		execDir := filepath.Dir(execPath)

		if path := filepath.Join(execDir, "config.yml"); fileExists(path) {
			return path
		}

		if path := filepath.Join(execDir, "..", "config.yml"); fileExists(path) {
			absPath, _ := filepath.Abs(path)
			return absPath
		}
	}

	if path := filepath.Join("config.yml"); fileExists(path) {
		absPath, _ := filepath.Abs(path)
		return absPath
	}

	if path := filepath.Join("scripts", "tui-manager", "config.yml"); fileExists(path) {
		absPath, _ := filepath.Abs(path)
		return absPath
	}

	homeDir, _ := os.UserHomeDir()
	paths := []string{
		filepath.Join(homeDir, "AppData", "Local", "apicortex-manager", "config.yml"),
		"./config.yml",
		"../config.yml",
		"../../scripts/tui-manager/config.yml",
	}

	for _, p := range paths {
		if fileExists(p) {
			absPath, _ := filepath.Abs(p)
			return absPath
		}
	}

	return ""
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}

func (c *Config) GetService(name string) (*ServiceConfig, bool) {
	svc, ok := c.Services[name]
	return &svc, ok
}

func (c *Config) ResolveWorkingDir(relPath string) string {
	if filepath.IsAbs(relPath) {
		return relPath
	}

	absConfigDir, err := filepath.Abs(c.ConfigDir)
	if err != nil {
		absConfigDir = c.ConfigDir
	}

	candidates := []string{
		filepath.Clean(filepath.Join(absConfigDir, relPath)),
		filepath.Clean(filepath.Join(absConfigDir, "..", relPath)),
		filepath.Clean(filepath.Join(absConfigDir, "..", "..", relPath)),
		filepath.Clean(filepath.Join(absConfigDir, "..", "..", "..", relPath)),
		filepath.Clean(filepath.Join(c.ProjectRoot, relPath)),
	}

	for _, candidate := range candidates {
		if fileExists(candidate) {
			return candidate
		}
	}

	return filepath.Clean(filepath.Join(absConfigDir, relPath))
}
