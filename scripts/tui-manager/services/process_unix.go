//go:build !windows

package services

import (
	"os/exec"
	"syscall"
)

func setProcessGroup(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
}

func assignProcessToJob(pid int) (uintptr, error) {
	return 0, nil
}

func closeJob(handle uintptr) error {
	return nil
}
