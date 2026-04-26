package ui

import (
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"

	"apicortex-manager/config"
	"apicortex-manager/services"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
	"github.com/shirou/gopsutil/v4/cpu"
	gopsmem "github.com/shirou/gopsutil/v4/mem"
	"gopkg.in/yaml.v3"
)

const (
	TabDashboard = iota
	TabControlPlane
	TabIngest
	TabML
	TabFrontend
	TabApiTesting
	TabCloudflared
)

var (
	colorPrimary    = lipgloss.Color("#00d7ff")
	colorSuccess    = lipgloss.Color("#00ff87")
	colorError      = lipgloss.Color("#ff5faf")
	colorWarning    = lipgloss.Color("#ffaf00")
	colorBackground = lipgloss.Color("#1c1c1c")
	colorSurface    = lipgloss.Color("#2d2d2d")
	colorSurfaceAlt = lipgloss.Color("#3d3d3d")
	colorText       = lipgloss.Color("#e4e4e4")
	colorMuted      = lipgloss.Color("#808080")
)

type App struct {
	config          *config.Config
	manager         *services.Manager
	activeTab       int
	width           int
	height          int
	ready           bool
	logScroll       map[string]int
	showConfirm     bool
	confirmMsg      string
	confirmCallback func()
	startTime       time.Time
	serviceKeys     []string
	serviceNames    map[string]string
	sysMem          uint64
	sysCPU          int
	sysCPUPercent   float64
	sysRAMPercent   float64
	sysGOMAXPROCS   int
	sysGoroutines   int
	sysHeapAlloc    uint64
	sysHeapSys      uint64
	sysTotalAlloc   uint64
	sysStackInuse   uint64
	sysSys          uint64
	sysMallocs      uint64
	sysFrees        uint64
	sysNextGC       uint64
	sysLastGCAgo    time.Duration
	sysNumGC        uint32
	sysPauseTotal   uint64
	tunnelRoutes    []tunnelRouteCheck
	tunnelStatus    map[string]tunnelRouteStatus
	tunnelLastCheck time.Time
	dockerAvailable bool
	dockerError     string
	dockerLastCheck time.Time
}

type tickMsg struct{}

type cloudflaredStatusMsg struct {
	CheckedAt       time.Time
	DockerAvailable bool
	DockerError     string
	Routes          []tunnelRouteStatus
}

type tunnelRouteCheck struct {
	Hostname string
	Probes   []string
}

type tunnelRouteStatus struct {
	Hostname   string
	TargetURL  string
	Alive      bool
	StatusCode int
	Error      string
	CheckedAt  time.Time
}

func NewApp(cfg *config.Config) *App {
	serviceKeys := []string{"controlplane", "ingest", "ml", "frontend", "api_testing", "cloudflared"}
	serviceNames := map[string]string{
		"controlplane": "Control Plane",
		"ingest":       "Ingest Service",
		"ml":           "ML Worker",
		"frontend":     "Frontend",
		"api_testing":  "API Testing Engine",
		"cloudflared":  "Cloudflared Tunnel",
	}

	tunnelRoutes := buildTunnelRouteChecks(cfg)
	tunnelStatus := make(map[string]tunnelRouteStatus, len(tunnelRoutes))
	for _, route := range tunnelRoutes {
		target := ""
		if len(route.Probes) > 0 {
			target = route.Probes[0]
		}
		tunnelStatus[route.Hostname] = tunnelRouteStatus{
			Hostname:  route.Hostname,
			TargetURL: target,
		}
	}

	app := &App{
		config:       cfg,
		activeTab:    TabDashboard,
		startTime:    time.Now(),
		logScroll:    make(map[string]int),
		manager:      services.NewManager(cfg),
		serviceKeys:  serviceKeys,
		serviceNames: serviceNames,
		tunnelRoutes: tunnelRoutes,
		tunnelStatus: tunnelStatus,
	}

	for _, key := range serviceKeys {
		if key == "cloudflared" {
			continue
		}
		_ = app.manager.StartService(key)
	}

	return app
}

func (a *App) Init() tea.Cmd {
	return tea.Batch(
		tea.Tick(1*time.Second, func(t time.Time) tea.Msg {
			return tickMsg{}
		}),
		a.cloudflaredStatusCmd(true),
	)
}

func (a *App) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		return a.handleKey(msg)
	case tea.WindowSizeMsg:
		a.width = msg.Width
		a.height = msg.Height
		a.ready = true
	case tickMsg:
		a.updateMetrics()
		cmds := []tea.Cmd{
			tea.Tick(1*time.Second, func(t time.Time) tea.Msg {
				return tickMsg{}
			}),
		}
		if a.shouldRefreshTunnelStatus(false) {
			cmds = append(cmds, a.cloudflaredStatusCmd(false))
		}
		return a, tea.Batch(cmds...)
	case cloudflaredStatusMsg:
		a.applyCloudflaredStatus(msg)
	}
	return a, nil
}

func (a *App) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	if a.showConfirm {
		switch msg.Type {
		case tea.KeyEnter:
			if strings.ToLower(msg.String()) == "y" {
				if a.confirmCallback != nil {
					a.confirmCallback()
				}
			}
		case tea.KeyRunes:
			if strings.ToLower(msg.String()) == "y" {
				if a.confirmCallback != nil {
					a.confirmCallback()
				}
			}
		}
		a.showConfirm = false
		return a, nil
	}

	switch msg.Type {
	case tea.KeyCtrlC, tea.KeyEsc:
		_ = a.saveSessionLogs()
		a.manager.StopAll()
		return a, tea.Quit
	}

	serviceKey := ""
	if a.activeTab != TabDashboard {
		serviceKey = a.serviceKeys[a.activeTab-1]
	}

	key := msg.String()
	keyLower := strings.ToLower(key)

	if serviceKey != "" {
		svc, _ := a.manager.GetService(serviceKey)
		totalLogs := 0
		if svc != nil {
			totalLogs = len(svc.GetLogs(1000))
		}
		logHeight := a.serviceLogHeight()
		startIdx, maxStart := a.resolveLogScroll(serviceKey, totalLogs, logHeight)
		switch {
		case keyLower == "pgup" || keyLower == "up" || keyLower == "k":
			startIdx = max(0, startIdx-10)
			a.logScroll[serviceKey] = startIdx
			return a, nil
		case keyLower == "pgdn" || keyLower == "pgdown" || keyLower == "down" || keyLower == "j":
			startIdx = min(maxStart, startIdx+10)
			a.logScroll[serviceKey] = startIdx
			return a, nil
		case keyLower == "g":
			startIdx = 0
			a.logScroll[serviceKey] = startIdx
			return a, nil
		case key == "G":
			startIdx = maxStart
			a.logScroll[serviceKey] = startIdx
			return a, nil
		}
	}

	switch keyLower {
	case "q":
		_ = a.saveSessionLogs()
		a.manager.StopAll()
		return a, tea.Quit
	case "0":
		a.activeTab = TabDashboard
	case "1":
		a.activeTab = TabControlPlane
	case "2":
		a.activeTab = TabIngest
	case "3":
		a.activeTab = TabML
	case "4":
		a.activeTab = TabFrontend
	case "5":
		a.activeTab = TabApiTesting
	case "6":
		a.activeTab = TabCloudflared
	case "f":
		if a.activeTab == TabCloudflared {
			return a, a.cloudflaredStatusCmd(true)
		}
	case "s":
		if serviceKey != "" {
			svc, _ := a.manager.GetService(serviceKey)
			if svc != nil && svc.Status == services.StatusRunning {
				a.showConfirm = true
				a.confirmMsg = fmt.Sprintf("Stop %s? (y/n)", svc.Name)
				a.confirmCallback = func() { a.manager.StopService(serviceKey) }
			} else {
				a.showConfirm = true
				a.confirmMsg = fmt.Sprintf("Start %s? (y/n)", a.serviceNames[serviceKey])
				a.confirmCallback = func() { _ = a.manager.StartService(serviceKey) }
			}
		} else {
			if a.anyServiceRunning() {
				a.showConfirm = true
				a.confirmMsg = "Stop all services? (y/n)"
				a.confirmCallback = func() { a.manager.StopAll() }
			} else {
				a.showConfirm = true
				a.confirmMsg = "Start all services? (y/n)"
				a.confirmCallback = func() {
					for _, key := range a.serviceKeys {
						_ = a.manager.StartService(key)
					}
				}
			}
		}
	case "r":
		if serviceKey != "" {
			a.showConfirm = true
			a.confirmMsg = fmt.Sprintf("Restart %s? (y/n)", a.serviceNames[serviceKey])
			a.confirmCallback = func() {
				a.manager.StopService(serviceKey)
				time.Sleep(500 * time.Millisecond)
				_ = a.manager.StartService(serviceKey)
			}
		} else {
			a.showConfirm = true
			a.confirmMsg = "Restart all services? (y/n)"
			a.confirmCallback = func() {
				a.manager.StopAll()
				time.Sleep(500 * time.Millisecond)
				for _, key := range a.serviceKeys {
					_ = a.manager.StartService(key)
				}
			}
		}
	}

	return a, nil
}

func (a *App) anyServiceRunning() bool {
	for _, key := range a.serviceKeys {
		svc, ok := a.manager.GetService(key)
		if ok && svc != nil && svc.Status == services.StatusRunning {
			return true
		}
	}
	return false
}

func formatBytes(bytes uint64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	d := float64(bytes) / unit
	suffix := []string{"KB", "MB", "GB", "TB"}
	for _, s := range suffix {
		if d < unit {
			return fmt.Sprintf("%.2f %s", d, s)
		}
		d /= unit
	}
	return fmt.Sprintf("%.2f PB", d)
}

func (a *App) saveSessionLogs() error {
	timestamp := time.Now().Format("20060102_150405")
	logDir := filepath.Join(".", "logs")
	if err := os.MkdirAll(logDir, 0o755); err != nil {
		return err
	}
	filename := filepath.Join(logDir, fmt.Sprintf("apicortex-session-%s.log", timestamp))

	var sb strings.Builder
	for _, key := range a.serviceKeys {
		svc, ok := a.manager.GetService(key)
		if !ok || svc == nil {
			continue
		}
		logs := svc.GetLogs(5000)
		for _, line := range logs {
			sb.WriteString(fmt.Sprintf("%s [%s] %s\n", line.Timestamp.Format(time.RFC3339), line.Service, line.Raw))
		}
	}

	return os.WriteFile(filename, []byte(sb.String()), 0o644)
}

func (a *App) updateMetrics() {
	var rtMem runtime.MemStats
	runtime.ReadMemStats(&rtMem)
	a.sysMem = rtMem.Alloc
	a.sysCPU = runtime.NumCPU()
	if cpuUsage, err := cpu.Percent(0, false); err == nil && len(cpuUsage) > 0 {
		a.sysCPUPercent = cpuUsage[0]
	}
	if vm, err := gopsmem.VirtualMemory(); err == nil {
		a.sysRAMPercent = vm.UsedPercent
	}
	a.sysGOMAXPROCS = runtime.GOMAXPROCS(0)
	a.sysGoroutines = runtime.NumGoroutine()
	a.sysHeapAlloc = rtMem.HeapAlloc
	a.sysHeapSys = rtMem.HeapSys
	a.sysTotalAlloc = rtMem.TotalAlloc
	a.sysStackInuse = rtMem.StackInuse
	a.sysSys = rtMem.Sys
	a.sysMallocs = rtMem.Mallocs
	a.sysFrees = rtMem.Frees
	a.sysNextGC = rtMem.NextGC
	a.sysNumGC = rtMem.NumGC
	a.sysPauseTotal = rtMem.PauseTotalNs
	if rtMem.LastGC > 0 {
		a.sysLastGCAgo = time.Since(time.Unix(0, int64(rtMem.LastGC)))
	} else {
		a.sysLastGCAgo = 0
	}
}

func (a *App) View() string {
	if !a.ready {
		return "\n\n  Initializing ApiCortex Manager...\n\n"
	}

	if a.showConfirm {
		return a.renderConfirm()
	}

	return a.renderMain()
}

func (a *App) renderMain() string {
	var sb strings.Builder

	sb.WriteString(a.renderHeader())
	sb.WriteString("\n")

	sb.WriteString(a.renderTabBar())
	sb.WriteString("\n")

	contentHeight := a.height - 6
	if contentHeight < 10 {
		contentHeight = 10
	}

	switch a.activeTab {
	case TabDashboard:
		sb.WriteString(a.renderDashboard(contentHeight))
	default:
		serviceIdx := a.activeTab - 1
		if serviceIdx >= 0 && serviceIdx < len(a.serviceKeys) {
			sb.WriteString(a.renderServiceDetail(a.serviceKeys[serviceIdx], contentHeight))
		}
	}

	sb.WriteString("\n")
	sb.WriteString(a.renderFooter())

	return sb.String()
}

func (a *App) renderHeader() string {
	title := "apicortex-manager"
	info := "System offline"
	if a.anyServiceRunning() {
		uptime := time.Since(a.startTime).Truncate(time.Second)
		info = fmt.Sprintf("Uptime: %s • %s", uptime, time.Now().Format("15:04:05"))
	}

	left := lipgloss.NewStyle().Bold(true).Foreground(colorPrimary).Render(" " + title)
	right := lipgloss.NewStyle().Foreground(colorMuted).Render(info + " ")

	maxWidth := a.width - 4
	if lipgloss.Width(left)+lipgloss.Width(right) <= maxWidth {
		line := left + strings.Repeat(" ", max(1, maxWidth-lipgloss.Width(left)-lipgloss.Width(right))) + right
		headerBox := lipgloss.NewStyle().Background(colorSurface).Foreground(colorText).Padding(0, 1).Width(a.width).Align(lipgloss.Left)
		return headerBox.Render(line)
	}

	line := left + "\n" + right
	headerBox := lipgloss.NewStyle().Background(colorSurface).Foreground(colorText).Padding(0, 1).Width(a.width).Align(lipgloss.Left)
	return headerBox.Render(line)
}

func (a *App) renderTabBar() string {
	tabs := []struct {
		name string
		id   int
	}{
		{"0 Dash", TabDashboard},
		{"1 CP", TabControlPlane},
		{"2 Ingest", TabIngest},
		{"3 ML", TabML},
		{"4 Front", TabFrontend},
		{"5 API", TabApiTesting},
		{"6 Tunnel", TabCloudflared},
	}

	var parts []string
	for _, tab := range tabs {
		label := " " + tab.name + " "
		if a.activeTab == tab.id {
			parts = append(parts, lipgloss.NewStyle().Background(colorPrimary).Foreground(colorBackground).Bold(true).Padding(0, 1).Render(label))
		} else {
			parts = append(parts, lipgloss.NewStyle().Foreground(colorMuted).Padding(0, 1).Render(label))
		}
	}

	bar := strings.Join(parts, "")
	if lipgloss.Width(bar) > a.width {
		bar = truncateString(bar, max(0, a.width-3)) + "..."
	}
	barStyle := lipgloss.NewStyle().
		Background(colorSurface).
		Foreground(colorText).
		Width(a.width).
		MaxWidth(a.width).
		Padding(0, 0)
	return barStyle.Render(bar)
}

func (a *App) renderDashboard(height int) string {
	var sb strings.Builder

	statsHeight := 7
	if height < 16 {
		statsHeight = 6
	}
	sb.WriteString(a.renderSystemStats(statsHeight))
	sb.WriteString("\n")

	remainingHeight := height - statsHeight - 1
	if remainingHeight < 6 {
		remainingHeight = 6
	}

	cardWidth := max(32, (a.width-8)/2)
	rowCount := (len(a.serviceKeys) + 1) / 2
	if rowCount < 1 {
		rowCount = 1
	}
	rowGap := 1
	cardHeight := (remainingHeight - (rowCount-1)*rowGap) / rowCount
	if cardHeight < 6 {
		cardHeight = 6
	}

	for row := 0; row < rowCount; row++ {
		var rowCards []string
		for col := 0; col < 2; col++ {
			idx := row*2 + col
			if idx < len(a.serviceKeys) {
				rowCards = append(rowCards, a.renderServiceCard(a.serviceKeys[idx], cardWidth, cardHeight))
			}
		}
		sb.WriteString(lipgloss.JoinHorizontal(lipgloss.Top, rowCards...))
		if row < rowCount-1 {
			sb.WriteString("\n")
		}
	}

	return sb.String()
}

func (a *App) renderFooter() string {
	helpText := "[0] Dashboard  [1-6] Services  [s] Start/Stop  [r] Restart  [PgUp/PgDn] Scroll  [q]/[Esc] Quit"
	if a.activeTab != TabDashboard {
		helpText = "[PgUp/PgDn or ↑/↓] Scroll  [g/G] Top/Bottom  [s] Start/Stop  [r] Restart  [0] Dashboard  [q]/[Esc] Quit"
		if a.activeTab == TabCloudflared {
			helpText = "[f] Refresh Docker/Routes  [s] Start/Stop  [r] Restart  [PgUp/PgDn] Scroll  [g/G] Top/Bottom  [0] Dashboard  [q]/[Esc] Quit"
		}
	}
	style := lipgloss.NewStyle().
		Background(colorBackground).
		Foreground(colorMuted).
		Padding(0, 1).
		Width(a.width).
		MaxWidth(a.width)
	return style.Render(helpText)
}

func (a *App) renderSystemStats(height int) string {
	running := 0
	healthy := 0
	for _, key := range a.serviceKeys {
		svc, _ := a.manager.GetService(key)
		if svc != nil && svc.Status == services.StatusRunning {
			running++
			if svc.Health {
				healthy++
			}
		}
	}

	uptime := time.Since(a.startTime).Truncate(time.Second)
	routesAlive := 0
	totalRoutes := 0
	for _, route := range a.currentTunnelRouteStatuses() {
		totalRoutes++
		if route.Alive {
			routesAlive++
		}
	}

	dockerState := "down"
	if a.dockerAvailable {
		dockerState = "up"
	}

	leftRows := []string{
		fmt.Sprintf("CPU %.1f%%  RAM %.1f%%", a.sysCPUPercent, a.sysRAMPercent),
		fmt.Sprintf("AppMem %s  Heap %s", formatBytes(a.sysMem), formatBytes(a.sysHeapAlloc)),
		fmt.Sprintf("Go %s  Cores %d", runtime.Version(), a.sysCPU),
		fmt.Sprintf("Running %d/%d  Uptime %s", running, len(a.serviceKeys), uptime),
	}
	rightRows := []string{
		fmt.Sprintf("Healthy %d/%d  Tunnel %d/%d", healthy, len(a.serviceKeys), routesAlive, totalRoutes),
		fmt.Sprintf("Docker %s  Time %s", dockerState, time.Now().Format("15:04:05")),
		fmt.Sprintf("GOMAXPROCS %d  Goroutines %d", a.sysGOMAXPROCS, a.sysGoroutines),
		fmt.Sprintf("GC count %d  Last GC %s ago", a.sysNumGC, a.sysLastGCAgo.Truncate(time.Second)),
	}

	innerWidth := max(24, a.width-8)
	gap := "   "
	leftWidth := max(12, innerWidth/2-2)
	rightWidth := max(12, innerWidth-leftWidth-len(gap))
	rowCount := min(len(leftRows), len(rightRows))
	rows := make([]string, 0, rowCount)
	for i := 0; i < rowCount; i++ {
		left := truncateString(leftRows[i], leftWidth)
		right := truncateString(rightRows[i], rightWidth)
		leftCell := lipgloss.NewStyle().Width(leftWidth).MaxWidth(leftWidth).Align(lipgloss.Left).Render(left)
		rightCell := lipgloss.NewStyle().Width(rightWidth).MaxWidth(rightWidth).Align(lipgloss.Left).Render(right)
		rows = append(rows, leftCell+gap+rightCell)
	}
	content := strings.Join(rows, "\n")

	// Build short URL status summary
	type hostURLStatus struct {
		label string
		alive bool
	}
	statuses := make([]hostURLStatus, 0, 5)
	for _, key := range []string{"controlplane", "ingest", "frontend", "api_testing"} {
		svcCfg, ok := a.config.GetService(key)
		if !ok || strings.TrimSpace(svcCfg.HealthCheck) == "" {
			continue
		}
		alive := false
		svc, ok := a.manager.GetService(key)
		if ok && svc != nil && svc.Status == services.StatusRunning && svc.Health {
			alive = true
		}
		shortName := ""
		switch key {
		case "controlplane": shortName = "CP"
		case "ingest": shortName = "Ingest"
		case "frontend": shortName = "Front"
		case "api_testing": shortName = "API"
		}
		statuses = append(statuses, hostURLStatus{label: shortName, alive: alive})
	}

	tunnelAlive := false
	tunnelRoutes := 0
	for _, route := range a.currentTunnelRouteStatuses() {
		tunnelRoutes++
		if route.Alive {
			tunnelAlive = true
		}
	}
	if tunnelRoutes > 0 {
		statuses = append(statuses, hostURLStatus{label: "Tunnel", alive: tunnelAlive})
	}

	urlsParts := make([]string, 0, len(statuses))
	for _, st := range statuses {
		state := "✗"
		stateColor := colorError
		if st.alive {
			state = "✓"
			stateColor = colorSuccess
		}
		urlsParts = append(urlsParts, lipgloss.NewStyle().Foreground(colorMuted).Render(st.label+":")+
			lipgloss.NewStyle().Foreground(stateColor).Render(state))
	}
	urlsStr := strings.Join(urlsParts, lipgloss.NewStyle().Foreground(colorMuted).Render(" • "))

	titleStr := lipgloss.NewStyle().Bold(true).Foreground(colorPrimary).Render(" System Status ")
	
	headerWidth := a.width - 2
	spaces := headerWidth - lipgloss.Width(titleStr) - lipgloss.Width(" "+urlsStr+" ")
	if spaces < 1 {
		spaces = 1
	}
	headerLine := titleStr + strings.Repeat(" ", spaces) + " " + urlsStr + " "

	card := lipgloss.NewStyle().
		Background(colorSurface).
		Foreground(colorText).
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorPrimary).
		Padding(0, 1).
		Width(a.width - 2).
		Height(max(6, min(height, 8))).
		Align(lipgloss.Left)

	return card.Render(headerLine + "\n" + content)
}

func (a *App) renderServiceCard(serviceKey string, width, height int) string {
	svc, _ := a.manager.GetService(serviceKey)

	if svc == nil {
		if serviceKey == "cloudflared" {
			dockerLine := "Docker: checking..."
			routeLine := "Routes: checking..."
			if !a.dockerLastCheck.IsZero() {
				if a.dockerAvailable {
					dockerLine = "Docker: ✓ Available"
				} else {
					dockerLine = "Docker: ✗ Unavailable"
				}
				routes := a.currentTunnelRouteStatuses()
				alive := 0
				for _, route := range routes {
					if route.Alive {
						alive++
					}
				}
				routeLine = fmt.Sprintf("Routes: %d/%d alive", alive, len(routes))
			}

			content := fmt.Sprintf("  %s\n  Status: %s\n  %s\n  %s\n\n  Press [5] then [f] to refresh\n  Press [s] to start tunnel",
				a.serviceNames[serviceKey],
				"Not started",
				dockerLine,
				routeLine,
			)

			style := lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorMuted).
				Background(colorSurface).
				Foreground(colorText).
				Width(width).
				Height(height-2).
				Padding(1, 1)

			return style.Render(content)
		}

		style := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(colorMuted).
			Background(colorSurface).
			Width(width).
			Height(height-2).
			Padding(1, 1)
		return style.Render("Not started")
	}

	status := svc.Status.String()
	statusColor := colorMuted

	if svc.Status == services.StatusRunning && svc.Health {
		statusColor = colorSuccess
		status = "✓ Running"
	} else if svc.Status == services.StatusRunning && !svc.Health {
		statusColor = colorWarning
		status = "⚠ Running (Unhealthy)"
	} else if svc.Status == services.StatusError {
		statusColor = colorError
		status = "✗ Error"
	} else if svc.Status == services.StatusStarting {
		statusColor = colorWarning
		status = "⟳ Starting"
	}

	borderColor := colorSurface
	if svc.Status == services.StatusRunning && svc.Health {
		borderColor = colorSuccess
	} else if svc.Status == services.StatusError {
		borderColor = colorError
	}

	name := a.serviceNames[serviceKey]
	port := ""
	if svc.Config.Port > 0 {
		port = fmt.Sprintf("\n  Port: %d", svc.Config.Port)
	}

	logs := svc.GetLogs(4)
	logLines := make([]string, 0)
	if len(logs) == 0 {
		logLines = append(logLines, "[Waiting for logs...]")
	} else {
		for _, log := range logs {
			line := truncateString(log.Raw, width-6)
			logLines = append(logLines, line)
		}
	}

	logContent := strings.Join(logLines, "\n")

	content := fmt.Sprintf(
		"  %s\n"+
			"  Status: %s%s\n\n"+
			"  Logs:\n%s",
		name,
		status,
		port,
		logContent,
	)

	statusStyle := lipgloss.NewStyle().Foreground(statusColor).Bold(true)
	content = strings.Replace(content, status, statusStyle.Render(status), 1)

	style := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(borderColor).
		Background(colorSurface).
		Foreground(colorText).
		Width(width).
		Height(height-2).
		Padding(1, 1)

	return style.Render(content)
}

func (a *App) renderHostStatusCard(width, height int) string {
	type hostURLStatus struct {
		label string
		url   string
		alive bool
	}

	statuses := make([]hostURLStatus, 0, 10)
	for _, key := range []string{"controlplane", "ingest", "frontend"} {
		svcCfg, ok := a.config.GetService(key)
		if !ok || strings.TrimSpace(svcCfg.HealthCheck) == "" {
			continue
		}
		alive := false
		svc, ok := a.manager.GetService(key)
		if ok && svc != nil && svc.Status == services.StatusRunning && svc.Health {
			alive = true
		}
		statuses = append(statuses, hostURLStatus{
			label: "localhost",
			url:   strings.TrimSpace(svcCfg.HealthCheck),
			alive: alive,
		})
	}

	for _, route := range a.currentTunnelRouteStatuses() {
		urlValue := strings.TrimSpace(route.TargetURL)
		if urlValue == "" {
			urlValue = "https://" + strings.TrimSpace(route.Hostname)
		}
		statuses = append(statuses, hostURLStatus{
			label: "tunnel",
			url:   urlValue,
			alive: route.Alive,
		})
	}

	lineWidth := max(20, width-8)
	maxRows := max(2, height-6)
	rows := make([]string, 0, maxRows)
	for i, item := range statuses {
		if i >= maxRows {
			break
		}
		state := "DEAD"
		stateStyle := lipgloss.NewStyle().Foreground(colorError).Bold(true)
		if item.alive {
			state = "LIVE"
			stateStyle = lipgloss.NewStyle().Foreground(colorSuccess).Bold(true)
		}
		prefix := lipgloss.NewStyle().Foreground(colorMuted).Render("[" + item.label + "]")
		urlText := truncateString(item.url, max(8, lineWidth-20))
		row := fmt.Sprintf("%s %s %s", prefix, urlText, stateStyle.Render(state))
		rows = append(rows, row)
	}

	if len(rows) == 0 {
		rows = append(rows, lipgloss.NewStyle().Foreground(colorMuted).Render("No host URLs configured"))
	}

	content := "  Host URLs\n" + strings.Join(rows, "\n")

	style := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorPrimary).
		Background(colorSurface).
		Foreground(colorText).
		Width(width).
		Height(height-2).
		Padding(1, 1)

	return style.Render(content)
}

func (a *App) renderServiceDetail(serviceKey string, height int) string {
	svc, _ := a.manager.GetService(serviceKey)
	if serviceKey == "cloudflared" {
		return a.renderCloudflaredDetail(svc, height)
	}

	if svc == nil {
		return "Service not available"
	}

	var sb strings.Builder

	statusColor := colorMuted
	if svc.Status == services.StatusRunning && svc.Health {
		statusColor = colorSuccess
	} else if svc.Status == services.StatusError {
		statusColor = colorError
	}

	statusStr := svc.Status.String()
	header := fmt.Sprintf("┌ %s • Status: %s", a.serviceNames[serviceKey], statusStr)
	headerStyle := lipgloss.NewStyle().
		Foreground(colorPrimary).
		Bold(true)
	sb.WriteString(headerStyle.Render(header))
	sb.WriteString("\n\n")

	pid := 0

	infoContent := fmt.Sprintf(
		"Command:         %s\n"+
			"Args:            %s\n"+
			"Working Dir:     %s\n"+
			"Port:            %d\n"+
			"Status:          %s\n"+
			"PID:             %d",
		svc.Config.Command,
		strings.Join(svc.Config.Args, " "),
		svc.Config.WorkingDir,
		svc.Config.Port,
		statusStr,
		pid,
	)

	infoStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorPrimary).
		Background(colorSurface).
		Foreground(colorText).
		Padding(1, 2).
		Width(min(a.width-4, 80))

	sb.WriteString(infoStyle.Render(infoContent))
	sb.WriteString("\n\n")

	sb.WriteString(lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render("📜 Recent Logs"))
	sb.WriteString("\n")

	logs := svc.GetLogs(1000)
	logLines := make([]string, 0)

	if len(logs) == 0 {
		logLines = []string{"[No logs yet]"}
	} else {
		logBoxWidth := min(a.width-4, 120)
		logInnerWidth := max(16, logBoxWidth-4)
		for _, log := range logs {
			color := colorText
			switch log.Level {
			case "ERROR":
				color = colorError
			case "WARN":
				color = colorWarning
			case "INFO":
				color = colorSuccess
			}
			clamped := truncateString(log.Raw, logInnerWidth)
			logLines = append(logLines, lipgloss.NewStyle().Foreground(color).Render(clamped))
		}
	}

	logHeight := a.serviceLogHeight()
	startIdx, _ := a.resolveLogScroll(serviceKey, len(logLines), logHeight)

	endIdx := min(startIdx+logHeight, len(logLines))
	displayLogs := logLines[startIdx:endIdx]

	logContent := strings.Join(displayLogs, "\n")
	logBoxWidth := min(a.width-4, 120)
	logStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorPrimary).
		Background(colorSurface).
		Foreground(colorText).
		Padding(1, 1).
		Width(logBoxWidth).
		Height(logHeight)

	sb.WriteString(logStyle.Render(logContent))
	sb.WriteString("\n")

	if len(logLines) > 0 {
		pageInfo := fmt.Sprintf("Lines %d-%d of %d", startIdx+1, endIdx, len(logLines))
		sb.WriteString(lipgloss.NewStyle().Foreground(colorMuted).Render(pageInfo))
		sb.WriteString("\n")
	}

	controls := "[PgUp/PgDn or [A/[B] Scroll  [g/G] Top/Bottom  [0] Dashboard  [q] Quit"
	sb.WriteString(lipgloss.NewStyle().Foreground(colorMuted).Render(controls))

	_ = statusColor

	return sb.String()
}

func (a *App) renderCloudflaredDetail(svc *services.ServiceInstance, height int) string {
	var sb strings.Builder

	statusStr := "Not started"
	tunnelRunning := false
	if svc != nil {
		statusStr = svc.Status.String()
		tunnelRunning = svc.Status == services.StatusRunning
	}

	header := fmt.Sprintf("┌ %s • Status: %s", a.serviceNames["cloudflared"], statusStr)
	sb.WriteString(lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render(header))
	sb.WriteString("\n")

	dockerState := "Checking..."
	dockerColor := colorMuted
	if !a.dockerLastCheck.IsZero() {
		if a.dockerAvailable {
			dockerState = "Available"
			dockerColor = colorSuccess
		} else {
			dockerState = "Unavailable"
			dockerColor = colorError
		}
	}

	routes := a.currentTunnelRouteStatuses()
	aliveCount := 0
	for _, route := range routes {
		if route.Alive {
			aliveCount++
		}
	}

	lastDockerCheck := "never"
	if !a.dockerLastCheck.IsZero() {
		lastDockerCheck = a.dockerLastCheck.Format("15:04:05")
	}

	infoContent := fmt.Sprintf(
		"Docker:          %s\n"+
			"Last Check:      %s\n"+
			"Tunnel Running:  %t\n"+
			"Exposed Routes:  %d\n"+
			"Routes Alive:    %d",
		dockerState,
		lastDockerCheck,
		tunnelRunning,
		len(routes),
		aliveCount,
	)

	if !a.dockerAvailable && a.dockerError != "" {
		infoContent += "\n\nDocker Error:\n  " + truncateString(a.dockerError, 120)
	} else if !tunnelRunning {
		infoContent += "\n\nStart tunnel with [s], then refresh with [f]"
	}

	infoHeight := 7
	if !a.dockerAvailable && a.dockerError != "" {
		infoHeight = 10
	} else if !tunnelRunning {
		infoHeight = 9
	}

	infoBox := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorPrimary).
		Background(colorSurface).
		Foreground(colorText).
		Padding(1, 2).
		Width(min(a.width-4, 92)).
		Height(infoHeight)

	infoRendered := infoBox.Render(infoContent)
	if dockerState != "Checking..." {
		infoRendered = strings.Replace(infoRendered, dockerState, lipgloss.NewStyle().Foreground(dockerColor).Bold(true).Render(dockerState), 1)
	}

	sb.WriteString(infoRendered)
	sb.WriteString("\n")

	sb.WriteString(lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render("Tunnel Route Health"))
	sb.WriteString("\n")

	routeLines := make([]string, 0, len(routes))
	for _, route := range routes {
		mark := "•"
		markColor := colorMuted
		if route.Alive {
			mark = "✓"
			markColor = colorSuccess
		} else if !route.CheckedAt.IsZero() {
			mark = "✗"
			markColor = colorError
		}

		suffix := ""
		if route.Alive {
			suffix = fmt.Sprintf(" [%d]", route.StatusCode)
		} else if route.Error != "" {
			suffix = " " + truncateString(route.Error, 56)
		}

		urlLabel := route.TargetURL
		if urlLabel == "" {
			urlLabel = "(no probe target)"
		}

		line := fmt.Sprintf("%s %s  %s%s", mark, route.Hostname, urlLabel, suffix)
		routeLines = append(routeLines, lipgloss.NewStyle().Foreground(markColor).Render(truncateString(line, min(a.width-10, 110))))
	}

	if len(routeLines) == 0 {
		routeLines = append(routeLines, lipgloss.NewStyle().Foreground(colorMuted).Render("No exposed routes detected from cloudflared config."))
	}

	routeHeight := min(max(5, len(routeLines)+2), 8)

	routeBox := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorPrimary).
		Background(colorSurface).
		Foreground(colorText).
		Padding(1, 1).
		Width(min(a.width-4, 120)).
		Height(routeHeight)

	sb.WriteString(routeBox.Render(strings.Join(routeLines, "\n")))
	sb.WriteString("\n")

	sb.WriteString(lipgloss.NewStyle().Foreground(colorPrimary).Bold(true).Render("Recent Logs"))
	sb.WriteString("\n")

	logLines := []string{"[No logs yet]"}
	if svc != nil {
		logs := svc.GetLogs(1000)
		if len(logs) > 0 {
			logLines = make([]string, 0, len(logs))
			logBoxWidth := min(a.width-4, 120)
			logInnerWidth := max(16, logBoxWidth-4)
			for _, log := range logs {
				lineColor := colorText
				switch log.Level {
				case "ERROR":
					lineColor = colorError
				case "WARN":
					lineColor = colorWarning
				case "INFO":
					lineColor = colorSuccess
				}
				logLines = append(logLines, lipgloss.NewStyle().Foreground(lineColor).Render(truncateString(log.Raw, logInnerWidth)))
			}
		}
	}

	logHeight := height - (infoHeight + routeHeight + 15)
	if logHeight < 6 {
		logHeight = 6
	}
	if logHeight > 12 {
		logHeight = 12
	}
	startIdx, _ := a.resolveLogScroll("cloudflared", len(logLines), logHeight)
	endIdx := min(startIdx+logHeight, len(logLines))
	displayLogs := logLines[startIdx:endIdx]

	logStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorPrimary).
		Background(colorSurface).
		Foreground(colorText).
		Padding(1, 1).
		Width(min(a.width-4, 120)).
		Height(logHeight)

	sb.WriteString(logStyle.Render(strings.Join(displayLogs, "\n")))
	sb.WriteString("\n")
	if len(logLines) > 0 {
		sb.WriteString(lipgloss.NewStyle().Foreground(colorMuted).Render(fmt.Sprintf("Lines %d-%d of %d", startIdx+1, endIdx, len(logLines))))
		sb.WriteString("\n")
	}

	return sb.String()
}

func (a *App) shouldRefreshTunnelStatus(force bool) bool {
	if force {
		return true
	}
	if a.activeTab == TabCloudflared {
		return time.Since(a.tunnelLastCheck) >= 6*time.Second
	}
	svc, ok := a.manager.GetService("cloudflared")
	if !ok || svc == nil || svc.Status != services.StatusRunning {
		return false
	}
	return time.Since(a.tunnelLastCheck) >= 6*time.Second
}

func (a *App) cloudflaredStatusCmd(force bool) tea.Cmd {
	routeChecks := make([]tunnelRouteCheck, len(a.tunnelRoutes))
	copy(routeChecks, a.tunnelRoutes)
	tunnelRunning := false
	if svc, ok := a.manager.GetService("cloudflared"); ok && svc != nil {
		tunnelRunning = svc.Status == services.StatusRunning
	}
	if !force && !a.shouldRefreshTunnelStatus(false) {
		return nil
	}
	return func() tea.Msg {
		return collectCloudflaredStatus(routeChecks, tunnelRunning)
	}
}

func (a *App) applyCloudflaredStatus(msg cloudflaredStatusMsg) {
	a.tunnelLastCheck = msg.CheckedAt
	a.dockerLastCheck = msg.CheckedAt
	a.dockerAvailable = msg.DockerAvailable
	a.dockerError = msg.DockerError
	if a.tunnelStatus == nil {
		a.tunnelStatus = make(map[string]tunnelRouteStatus, len(msg.Routes))
	}
	for _, route := range msg.Routes {
		a.tunnelStatus[route.Hostname] = route
	}
}

func (a *App) currentTunnelRouteStatuses() []tunnelRouteStatus {
	tunnelRunning := false
	if svc, ok := a.manager.GetService("cloudflared"); ok && svc != nil {
		tunnelRunning = svc.Status == services.StatusRunning
	}

	results := make([]tunnelRouteStatus, 0, len(a.tunnelRoutes))
	for _, route := range a.tunnelRoutes {
		status, ok := a.tunnelStatus[route.Hostname]
		if ok {
			if !tunnelRunning {
				status.Alive = false
				status.StatusCode = 0
				status.Error = "tunnel not running"
			}
			results = append(results, status)
			continue
		}
		target := ""
		if len(route.Probes) > 0 {
			target = route.Probes[0]
		}
		fallback := tunnelRouteStatus{Hostname: route.Hostname, TargetURL: target}
		if !tunnelRunning {
			fallback.Error = "tunnel not running"
		}
		results = append(results, fallback)
	}
	return results
}

func collectCloudflaredStatus(routeChecks []tunnelRouteCheck, tunnelRunning bool) cloudflaredStatusMsg {
	now := time.Now()
	dockerErr := services.CheckDockerAvailability()
	msg := cloudflaredStatusMsg{
		CheckedAt:       now,
		DockerAvailable: dockerErr == nil,
		Routes:          make([]tunnelRouteStatus, 0, len(routeChecks)),
	}
	if dockerErr != nil {
		msg.DockerError = dockerErr.Error()
	}
	if !tunnelRunning {
		for _, route := range routeChecks {
			status := tunnelRouteStatus{Hostname: route.Hostname, CheckedAt: now}
			if len(route.Probes) > 0 {
				status.TargetURL = route.Probes[0]
			}
			status.Alive = false
			status.Error = "tunnel not running"
			msg.Routes = append(msg.Routes, status)
		}
		return msg
	}

	client := &http.Client{Timeout: 1200 * time.Millisecond}
	for _, route := range routeChecks {
		status := probeTunnelRoute(client, route, now)
		msg.Routes = append(msg.Routes, status)
	}

	return msg
}

func probeTunnelRoute(client *http.Client, route tunnelRouteCheck, checkedAt time.Time) tunnelRouteStatus {
	status := tunnelRouteStatus{
		Hostname:  route.Hostname,
		CheckedAt: checkedAt,
	}
	if len(route.Probes) > 0 {
		status.TargetURL = route.Probes[0]
	}

	lastErr := ""
	for _, probe := range route.Probes {
		resp, err := client.Get(probe)
		if err != nil {
			lastErr = err.Error()
			continue
		}
		_, _ = io.Copy(io.Discard, resp.Body)
		_ = resp.Body.Close()

		status.TargetURL = probe
		status.StatusCode = resp.StatusCode
		if resp.StatusCode >= 200 && resp.StatusCode < 400 {
			status.Alive = true
			status.Error = ""
			return status
		}
		lastErr = fmt.Sprintf("http %d", resp.StatusCode)
	}

	status.Alive = false
	status.Error = lastErr
	return status
}

type cloudflaredConfigFile struct {
	Ingress []struct {
		Hostname string `yaml:"hostname"`
		Service  string `yaml:"service"`
	} `yaml:"ingress"`
}

func buildTunnelRouteChecks(cfg *config.Config) []tunnelRouteCheck {
	routeChecks := make([]tunnelRouteCheck, 0, 8)
	serviceConfig, ok := cfg.GetService("cloudflared")
	if ok {
		cloudflaredDir := cfg.ResolveWorkingDir(serviceConfig.WorkingDir)
		configPath := filepath.Join(cloudflaredDir, "config.yml")
		data, err := os.ReadFile(configPath)
		if err == nil {
			var parsed cloudflaredConfigFile
			if yaml.Unmarshal(data, &parsed) == nil {
				for _, ingress := range parsed.Ingress {
					host := strings.TrimSpace(ingress.Hostname)
					if host == "" {
						continue
					}
					probes := tunnelProbesForHost(host, ingress.Service)
					if len(probes) == 0 {
						continue
					}
					routeChecks = append(routeChecks, tunnelRouteCheck{Hostname: host, Probes: probes})
				}
			}
		}
	}

	if len(routeChecks) > 0 {
		return routeChecks
	}

	return []tunnelRouteCheck{
		{Hostname: "apicortex-cp.0xarchit.is-a.dev", Probes: []string{"https://apicortex-cp.0xarchit.is-a.dev/health", "https://apicortex-cp.0xarchit.is-a.dev"}},
		{Hostname: "apicortex-ingest.0xarchit.is-a.dev", Probes: []string{"https://apicortex-ingest.0xarchit.is-a.dev/health", "https://apicortex-ingest.0xarchit.is-a.dev"}},
		{Hostname: "apicortex.0xarchit.is-a.dev", Probes: []string{"https://apicortex.0xarchit.is-a.dev", "https://apicortex.0xarchit.is-a.dev/health"}},
	}
}

func tunnelProbesForHost(hostname string, service string) []string {
	trimmedHost := strings.TrimSpace(hostname)
	if trimmedHost == "" {
		return nil
	}

	base := "https://" + trimmedHost
	trimmedService := strings.TrimSpace(service)
	if strings.HasPrefix(trimmedService, "http_status:") {
		return nil
	}

	probes := make([]string, 0, 4)
	preferRoot := false
	if parsed, err := url.Parse(trimmedService); err == nil {
		if parsed.Path != "" && parsed.Path != "/" {
			probes = append(probes, base+parsed.Path)
		}
		if parsed.Port() == "3000" {
			preferRoot = true
		}
	}

	if preferRoot {
		probes = append(probes, base, base+"/health")
	} else {
		probes = append(probes, base+"/health", base)
	}

	seen := make(map[string]struct{}, len(probes))
	unique := make([]string, 0, len(probes))
	for _, probe := range probes {
		if _, ok := seen[probe]; ok {
			continue
		}
		seen[probe] = struct{}{}
		unique = append(unique, probe)
	}

	return unique
}

func (a *App) serviceLogHeight() int {
	contentHeight := a.height - 6
	if contentHeight < 10 {
		contentHeight = 10
	}
	return max(8, contentHeight-20)
}

func (a *App) resolveLogScroll(serviceKey string, totalLogs int, logHeight int) (int, int) {
	if totalLogs < 0 {
		totalLogs = 0
	}
	if logHeight <= 0 {
		logHeight = 1
	}
	maxStart := max(0, totalLogs-logHeight)
	startIdx, hasScroll := a.logScroll[serviceKey]
	if !hasScroll {
		startIdx = maxStart
	}
	if startIdx < 0 {
		startIdx = 0
	}
	if startIdx > maxStart {
		startIdx = maxStart
	}
	return startIdx, maxStart
}

func (a *App) renderConfirm() string {
	style := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(colorError).
		Padding(2, 4).
		Background(colorSurface)

	content := fmt.Sprintf("\n⚠  %s\n\n[y] Yes  [n] No\n", a.confirmMsg)
	rendered := style.Render(content)

	lines := strings.Split(rendered, "\n")
	emptyLines := (a.height - len(lines)) / 2
	if emptyLines < 0 {
		emptyLines = 0
	}

	result := strings.Repeat("\n", emptyLines) + rendered
	return result
}

func (a *App) Run() error {
	_, _ = os.Stdout.WriteString("\x1b]0;apicortex-manager\x07")
	p := tea.NewProgram(a, tea.WithAltScreen())
	_, err := p.Run()
	return err
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func truncateString(s string, width int) string {
	runes := []rune(s)
	if len(runes) <= width {
		return s
	}
	if width <= 0 {
		return ""
	}
	return string(runes[:width])
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}
