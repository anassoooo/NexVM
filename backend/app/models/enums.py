from enum import Enum


class VMStatus(str, Enum):
    stopped = "stopped"
    starting = "starting"
    running = "running"
    stopping = "stopping"
    error = "error"


class LogStatus(str, Enum):
    success = "success"
    failure = "failure"


class LogAction(str, Enum):
    create_vm = "create_vm"
    start_vm = "start_vm"
    stop_vm = "stop_vm"
    delete_vm = "delete_vm"
    login = "login"
    ai_command = "ai_command"
    force_reset_vm = "force_reset_vm"
    attach_iso = "attach_iso"
    detach_iso = "detach_iso"
    enable_vrde = "enable_vrde"
    disable_vrde = "disable_vrde"
