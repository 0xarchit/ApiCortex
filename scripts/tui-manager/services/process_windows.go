//go:build windows

package services

import (
	"os/exec"
	"syscall"
)

func setProcessGroup(cmd *exec.Cmd) {

	cmd.SysProcAttr = &syscall.SysProcAttr{CreationFlags: syscall.CREATE_NEW_PROCESS_GROUP}
}

func assignProcessToJob(pid int) (uintptr, error) {
	return 0, nil
}

func closeJob(handle uintptr) error {
	return nil
}
