from enum import Enum


class VMStatus(str, Enum):
    stopped  = "stopped"
    starting = "starting"
    running  = "running"
    stopping = "stopping"
    paused   = "paused"
    error    = "error"


class LogStatus(str, Enum):
    success = "success"
    failure = "failure"


class LogAction(str, Enum):
    create_vm        = "create_vm"
    start_vm         = "start_vm"
    stop_vm          = "stop_vm"
    delete_vm        = "delete_vm"
    login            = "login"
    ai_command       = "ai_command"
    force_reset_vm   = "force_reset_vm"
    attach_iso       = "attach_iso"
    detach_iso       = "detach_iso"
    enable_vrde      = "enable_vrde"
    disable_vrde     = "disable_vrde"
    modify_vm        = "modify_vm"
    pause_vm         = "pause_vm"
    resume_vm        = "resume_vm"
    save_state       = "save_state"
    add_port_rule    = "add_port_rule"
    remove_port_rule = "remove_port_rule"
    take_snapshot    = "take_snapshot"
    restore_snapshot = "restore_snapshot"
    delete_snapshot  = "delete_snapshot"
    clone_vm         = "clone_vm"
    export_vm        = "export_vm"
    import_vm        = "import_vm"
