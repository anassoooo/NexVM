# Contract: VBoxManage Command Whitelist

**Branch**: `002-vm-management` | **Date**: 2026-04-06

This contract defines the **only five VBoxManage subcommands** permitted at runtime. No other VBoxManage commands may be added to production code without updating this contract and the corresponding whitelist in `vbox_wrapper.py`.

---

## Whitelist

| Action         | Exact subprocess arguments                                              | Timeout |
|----------------|-------------------------------------------------------------------------|---------|
| create_vm      | `[VBOXMANAGE_PATH, "createvm", "--name", <name>, "--register"]`        | 30s     |
| start_vm       | `[VBOXMANAGE_PATH, "startvm", <name>, "--type", "headless"]`           | 30s     |
| stop_vm        | `[VBOXMANAGE_PATH, "controlvm", <name>, "poweroff"]`                   | 30s     |
| delete_vm      | `[VBOXMANAGE_PATH, "unregistervm", <name>, "--delete"]`                | 30s     |
| get_vm_info    | `[VBOXMANAGE_PATH, "showvminfo", <name>, "--machinereadable"]`         | 10s     |

Where `<name>` is the VM's `name` field from the database — already validated as alphanumeric + hyphens + spaces (1–50 chars) at the API boundary.

---

## Enforcement

The `run_vbox_command` function in `services/vbox_wrapper.py` MUST reject any call whose second element (subcommand) is not in this whitelist. Rejection raises `ValueError` — it does NOT call subprocess.

```python
VBOXMANAGE_COMMANDS = {"createvm", "startvm", "controlvm", "unregistervm", "showvminfo"}

def run_vbox_command(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    assert cmd[1] in VBOXMANAGE_COMMANDS, f"Subcommand '{cmd[1]}' is not whitelisted"
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
```

---

## Return Code Interpretation

| returncode | Meaning                                         | Service action                              |
|------------|-------------------------------------------------|---------------------------------------------|
| 0          | Success                                         | Update VM status to success state           |
| non-zero   | VBoxManage reported an error                    | Set VM to "error", store stderr, log, raise |
| (exception `subprocess.TimeoutExpired`) | Subprocess timed out | Set VM to "error", error_message = "Command timed out", log, raise |

`stdout` is not used for status decisions. `stderr` is captured and stored in `error_message` on failure.

---

## Notes

- `shell=False` is always enforced (list argument form of `subprocess.run`).
- `<name>` is never constructed from raw HTTP input — it is always read from the validated `vms.name` column after passing Pydantic validation.
- `get_vm_info` (`showvminfo`) is used by `GET /api/v1/health` only. It is not called during normal CRUD operations.
- The `--type headless` flag for `startvm` means no display window is opened. This is required for server deployments and for single-tenant desktop deployments where a popup window would be unexpected.
- The `--delete` flag for `unregistervm` deletes the VM's disk files from the host filesystem. This is intentional and destructive — there is no recovery path.
