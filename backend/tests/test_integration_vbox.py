"""
Integration tests — real VBoxManage, no Supabase mocks.

Requires:
  - VirtualBox installed (VBOXMANAGE_PATH in .env)
  - Ubuntu ISO at UBUNTU_ISO_PATH

Run with:
  pytest tests/test_integration_vbox.py -v -m integration

Skipped automatically if VBoxManage or the ISO is not present.
"""

import os
import subprocess
import uuid

import pytest

from app.services.vbox_wrapper import (
    build_vbox_path,
    extract_vbox_uuid,
    parse_vbox_state,
    run_vbox_command,
)

UBUNTU_ISO_PATH = r"C:\Users\DELL\Downloads\ubuntu-20.04.6-desktop-amd64.iso"

VBOX = build_vbox_path()

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Skip guards
# ---------------------------------------------------------------------------

def _vbox_available() -> bool:
    try:
        r = subprocess.run([VBOX, "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

vbox_missing  = pytest.mark.skipif(not _vbox_available(),    reason="VBoxManage not available")
iso_missing   = pytest.mark.skipif(not os.path.isfile(UBUNTU_ISO_PATH), reason=f"ISO not found: {UBUNTU_ISO_PATH}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def test_vm_name():
    """Unique VM name for each test run — guarantees no collision."""
    uid = uuid.uuid4().hex[:8]
    return f"integ-test-{uid}"


@pytest.fixture()
def created_vm(test_vm_name):
    """
    Creates a minimal VirtualBox VM (no disk), yields its name, then
    unconditionally unregisters + deletes it even if the test fails.
    """
    vm_name = test_vm_name

    # Create + register
    result = subprocess.run(
        [VBOX, "createvm", "--name", vm_name, "--ostype", "Ubuntu_64", "--register"],
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, f"createvm failed:\n{result.stderr}"

    # Configure minimal hardware
    subprocess.run(
        [VBOX, "modifyvm", vm_name, "--memory", "512", "--cpus", "1",
         "--vram", "8", "--acpi", "on", "--ioapic", "on"],
        capture_output=True, text=True, timeout=30,
    )

    # Add SATA controller (needed for DVD attachment)
    subprocess.run(
        [VBOX, "storagectl", vm_name, "--name", "SATA",
         "--add", "sata", "--controller", "IntelAhci", "--portcount", "2"],
        capture_output=True, text=True, timeout=30,
    )

    yield vm_name

    # Teardown — always runs
    subprocess.run(
        [VBOX, "unregistervm", vm_name, "--delete"],
        capture_output=True, text=True, timeout=60,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@vbox_missing
def test_vboxmanage_version():
    """Sanity check — VBoxManage responds with a version string."""
    result = subprocess.run([VBOX, "--version"], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    assert result.stdout.strip()  # non-empty version string


@vbox_missing
def test_createvm_and_delete(test_vm_name):
    """create + unregister lifecycle — no ISO, no disk."""
    vm_name = test_vm_name

    create = subprocess.run(
        [VBOX, "createvm", "--name", vm_name, "--ostype", "Ubuntu_64", "--register"],
        capture_output=True, text=True, timeout=30,
    )
    assert create.returncode == 0, create.stderr
    vbox_id = extract_vbox_uuid(create.stdout)
    assert vbox_id is not None, "UUID not found in createvm output"

    delete = subprocess.run(
        [VBOX, "unregistervm", vm_name, "--delete"],
        capture_output=True, text=True, timeout=60,
    )
    assert delete.returncode == 0, delete.stderr


@vbox_missing
def test_showvminfo_state(created_vm):
    """showvminfo --machinereadable returns poweroff for a freshly created VM."""
    result = subprocess.run(
        [VBOX, "showvminfo", created_vm, "--machinereadable"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0, result.stderr
    state = parse_vbox_state(result.stdout)
    assert state == "poweroff"


@vbox_missing
@iso_missing
def test_attach_iso(created_vm):
    """Attach Ubuntu ISO as DVD, verify it appears in showvminfo, then detach."""
    # Attach ISO
    attach = subprocess.run(
        [VBOX, "storageattach", created_vm,
         "--storagectl", "SATA",
         "--port", "1", "--device", "0",
         "--type", "dvddrive",
         "--medium", UBUNTU_ISO_PATH],
        capture_output=True, text=True, timeout=30,
    )
    assert attach.returncode == 0, f"storageattach failed:\n{attach.stderr}"

    # Verify ISO appears in VM info
    info = subprocess.run(
        [VBOX, "showvminfo", created_vm, "--machinereadable"],
        capture_output=True, text=True, timeout=15,
    )
    assert result.returncode == 0 if (result := info) else True
    assert UBUNTU_ISO_PATH.replace("\\", "/") in info.stdout.replace("\\", "/") or \
           "ubuntu-20.04" in info.stdout.lower(), \
           f"ISO path not found in showvminfo output:\n{info.stdout[:500]}"

    # Detach ISO
    detach = subprocess.run(
        [VBOX, "storageattach", created_vm,
         "--storagectl", "SATA",
         "--port", "1", "--device", "0",
         "--type", "dvddrive",
         "--medium", "none"],
        capture_output=True, text=True, timeout=30,
    )
    assert detach.returncode == 0, f"detach failed:\n{detach.stderr}"

    # Verify ISO is gone
    info2 = subprocess.run(
        [VBOX, "showvminfo", created_vm, "--machinereadable"],
        capture_output=True, text=True, timeout=15,
    )
    assert "ubuntu-20.04" not in info2.stdout.lower()


@vbox_missing
def test_run_vbox_command_whitelist():
    """run_vbox_command rejects unlisted subcommands."""
    with pytest.raises(ValueError, match="not whitelisted"):
        run_vbox_command([VBOX, "list", "vms"])


@vbox_missing
def test_modifyvm_ram_cpu(created_vm):
    """modifyvm changes memory and CPU count — verified via showvminfo."""
    mod = subprocess.run(
        [VBOX, "modifyvm", created_vm, "--memory", "768", "--cpus", "2"],
        capture_output=True, text=True, timeout=15,
    )
    assert mod.returncode == 0, mod.stderr

    info = subprocess.run(
        [VBOX, "showvminfo", created_vm, "--machinereadable"],
        capture_output=True, text=True, timeout=15,
    )
    assert 'memory=768' in info.stdout
    assert 'cpus=2' in info.stdout


@vbox_missing
@iso_missing
def test_full_lifecycle(test_vm_name):
    """
    Full lifecycle: create → configure → attach ISO → verify → detach → delete.
    This mirrors what the service layer does for create_vm + attach_iso.
    """
    vm_name = test_vm_name
    try:
        # 1. Create
        r = subprocess.run(
            [VBOX, "createvm", "--name", vm_name, "--ostype", "Ubuntu_64", "--register"],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, r.stderr
        assert extract_vbox_uuid(r.stdout) is not None

        # 2. Hardware
        r = subprocess.run(
            [VBOX, "modifyvm", vm_name, "--memory", "512", "--cpus", "1",
             "--vram", "8", "--acpi", "on", "--ioapic", "on",
             "--boot1", "dvd", "--boot2", "none"],
            capture_output=True, text=True, timeout=15,
        )
        assert r.returncode == 0, r.stderr

        # 3. Storage controller
        r = subprocess.run(
            [VBOX, "storagectl", vm_name, "--name", "SATA", "--add", "sata",
             "--controller", "IntelAhci", "--portcount", "2"],
            capture_output=True, text=True, timeout=15,
        )
        assert r.returncode == 0, r.stderr

        # 4. Attach ISO
        r = subprocess.run(
            [VBOX, "storageattach", vm_name,
             "--storagectl", "SATA", "--port", "1", "--device", "0",
             "--type", "dvddrive", "--medium", UBUNTU_ISO_PATH],
            capture_output=True, text=True, timeout=30,
        )
        assert r.returncode == 0, r.stderr

        # 5. Verify state is poweroff and ISO is attached
        info = subprocess.run(
            [VBOX, "showvminfo", vm_name, "--machinereadable"],
            capture_output=True, text=True, timeout=15,
        )
        assert info.returncode == 0
        assert parse_vbox_state(info.stdout) == "poweroff"
        assert "ubuntu-20.04" in info.stdout.lower()

    finally:
        subprocess.run(
            [VBOX, "unregistervm", vm_name, "--delete"],
            capture_output=True, text=True, timeout=60,
        )
