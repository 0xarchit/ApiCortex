# ApiCortex TUI Manager

A terminal-based service manager for the ApiCortex platform. Start, stop, monitor, and manage all microservices from a single unified interface with live log streaming, health monitoring, and system metrics.

---

## Features

- **Unified Service Control**: Start, stop, and restart all ApiCortex services from one interface
- **Live Log Streaming**: Real-time log output from all services with color-coded severity levels
- **Health Monitoring**: Automatic health checks with visual status indicators
- **System Metrics**: CPU, memory, and uptime monitoring
- **Tabbed Interface**: Dashboard overview and individual service detail views
- **Keyboard Navigation**: Full keyboard-driven operation with intuitive shortcuts
- **Port Management**: Automatic port conflict detection and resolution
- **Confirmation Dialogs**: Safety prompts for destructive actions

---

## Quick Start

### Build

```bash
cd scripts/tui-manager
go build -o build/apicortex-manager.exe .
```

### Run

```bash
cd scripts/tui-manager/build
.\apicortex-manager.exe
```

### Configuration

The manager reads service definitions from `config.yml` in the same directory:

```yaml
services:
  controlplane:
    name: "Control Plane"
    command: "python"
    args: ["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    working_dir: "../../control-plane"
    health_check: "http://localhost:8000/health"
    port: 8000
```

---

## Interface

### Dashboard View

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ApiCortex Manager ● RUNNING          CPU: 4.2% | Mem: 42MB | Uptime: 5s│
├─────────────────────────────────────────────────────────────────────────┤
│ [Dashboard] [Control Plane] [Ingest] [ML] [Frontend]                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  SYSTEM OVERVIEW                                                        │
│  Services: 4/4 healthy                                                  │
│  CPU: 4.2%                                                              │
│  Memory: 42 MB                                                          │
│  Uptime: 5s                                                             │
│                                                                         │
│  CONTROL PLANE              INGEST SERVICE                              │
│  Status: Running            Status: Running                             │
│  Health: Healthy            Health: Healthy                             │
│  Press 1 for details        Press 2 for details                         │
│                                                                         │
│  ML WORKER                  FRONTEND                                    │
│  Status: Running            Status: Running                             │
│  Health: Healthy            Health: Healthy                             │
│  Press 3 for details        Press 4 for details                         │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ [0]Dashboard [1-4]Services [s]Stop [r]Restart [PgUp/PgDn]Scroll [q]Quit│
└─────────────────────────────────────────────────────────────────────────┘
```

### Service Detail View

```
┌─────────────────────────────────────────────────────────────────────────┐
│ ApiCortex Manager ● RUNNING          CPU: 4.2% | Mem: 42MB | Uptime: 5s│
├─────────────────────────────────────────────────────────────────────────┤
│ [Dashboard] [Control Plane] [Ingest] [ML] [Frontend]                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Control Plane  Status: Running                                         │
│                                                                         │
│  Working Directory: ../../control-plane                                 │
│  Port: 8000                                                             │
│                                                                         │
│  Live Logs:                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │ [12:00:01] INFO Starting uvicorn...                               │ │
│  │ [12:00:02] INFO Application startup complete                      │ │
│  │ [12:00:03] INFO Uvicorn running on http://0.0.0.0:8000            │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│  Showing 1-3 of 3 lines                                                 │
│  [g] Top  [G] Bottom  [PgUp/PgDn] Scroll  [0] Back to Dashboard       │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│ [0]Dashboard [1-4]Services [s]Stop [r]Restart [PgUp/PgDn]Scroll [q]Quit│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Keyboard Controls

### Global

| Key | Action |
|-----|--------|
| `0` | Switch to Dashboard |
| `1` | Control Plane detail |
| `2` | Ingest Service detail |
| `3` | ML Worker detail |
| `4` | Frontend detail |
| `s` | Stop all services |
| `r` | Restart all services |
| `q` / `Ctrl+C` | Quit |

### Log Navigation

| Key | Action |
|-----|--------|
| `PgUp` | Scroll up one page |
| `PgDn` | Scroll down one page |
| `g` | Go to top |
| `G` | Go to bottom |

### Dialogs

| Key | Action |
|-----|--------|
| `y` | Confirm action |
| `n` / `Esc` | Cancel action |

---

## Configuration

### config.yml Structure

```yaml
services:
  <service_key>:
    name: "<Display Name>"
    command: "<executable>"
    args: ["arg1", "arg2"]
    working_dir: "<relative or absolute path>"
    health_check: "<http_url or null>"
    port: <port_number>
    env:
      KEY: "value"
    pre_start:
      - command: "<command>"
        args: ["arg1"]
```

### Default Services

| Service | Port | Command |
|---------|------|---------|
| Control Plane | 8000 | Python/FastAPI |
| Ingest Service | 8080 | Go |
| ML Worker | - | Python |
| API Testing | 9090 | Rust |
| Frontend | 3000 | Bun/Next.js |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TUI Manager                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   UI Layer   │  │   Service    │  │   Config     │          │
│  │  (Bubbletea) │◄─┤   Manager    │◄─   Loader     │          │
│  │              │  │              │  │   (YAML)     │          │
│  └──────────────┘  └──────┬───────┘  └──────────────┘          │
│                           │                                     │
│                    ┌──────┴───────┐                             │
│                    │   Process    │                             │
│                    │   Spawner    │                             │
│                    └──────┬───────┘                             │
│                           │                                     │
│              ┌────────────┼────────────┐                        │
│              │            │            │                        │
│         ┌────┴────  ┌───┴────┐  ┌───┴────┐                    │
│         │Control  │  │Ingest  │  │  ML    │  ...               │
│         │Plane    │  │Service │  │Worker  │                    │
│         └─────────┘  └────────┘  └────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Requirements

- **Go**: 1.21 or later
- **Windows**: Windows 10/11 (primary platform)
- **Terminal**: Windows Terminal recommended for best experience

### Dependencies

```go
github.com/charmbracelet/bubbletea v1.3.10
github.com/charmbracelet/bubbles v1.0.0
github.com/charmbracelet/lipgloss v1.1.0
gopkg.in/yaml.v3 v3.0.1
```

---

## Troubleshooting

### Port Already in Use

The manager automatically detects and resolves port conflicts. If a service fails to start:

1. Check the service logs for port conflict messages
2. The manager will attempt to kill conflicting processes
3. Wait for port release (up to 5 seconds)
4. Restart the service with `r`

### Service Won't Start

1. Verify the `working_dir` path is correct
2. Check that the command exists in PATH
3. Review service logs for error messages
4. Ensure required dependencies are installed

### High Memory Usage

The manager buffers up to 5000 log lines per service. Memory usage is typically under 50MB.

---

## Development

### Build Commands

```bash
# Development build
go build -o build/apicortex-manager.exe .

# Optimized production build
go build -trimpath -buildvcs=false -ldflags="-s -w" -o build/apicortex-manager.exe .
```

### Project Structure

```
tui-manager/
├── main.go                 # Entry point
├── config.yml              # Service configuration
├── config/
│   └── config.go           # Configuration loader
├── services/
│   ├── manager.go          # Service lifecycle management
│   ├── port.go             # Port conflict resolution
│   └── process_windows.go  # Windows process handling
├── ui/
│   └── app.go              # TUI application
└── build/
    └── apicortex-manager.exe  # Compiled binary
```

---

```
┌─────────────────────────────────────────────────────────────────┐
│                     ApiCortex TUI Manager                       │
│                                                                 │
│  Version: 1.0.0                                                 │
│  Platform: Windows                                              │
│  Status: Production Ready                                       │
└─────────────────────────────────────────────────────────────────┘
```
