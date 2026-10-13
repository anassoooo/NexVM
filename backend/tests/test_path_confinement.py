"""Spec 012 F2 — user-supplied host paths must stay inside the configured directories."""

import os
import uuid
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.dependencies import get_current_user
from app.models.schemas import AIAttachISO, ISOAttachRequest, OVAExportRequest, OVAImportRequest
from app.routes.vm import router as vm_router
from app.services.vbox_wrapper import resolve_inside


def test_path_inside_base_is_accepted(tmp_path):
    target = tmp_path / "ubuntu.iso"
    assert resolve_inside(str(target), str(tmp_path)) == os.path.realpath(target)


def test_path_outside_base_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="inside"):
        resolve_inside(os.path.abspath(os.sep + "elsewhere.iso"), str(tmp_path))


def test_dotdot_escape_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        resolve_inside(str(tmp_path / ".." / "x.ova"), str(tmp_path))


def test_sibling_with_same_prefix_is_rejected(tmp_path):
    base = tmp_path / "exports"
    with pytest.raises(ValueError):
        resolve_inside(str(tmp_path / "exports-evil" / "x.ova"), str(base))


@pytest.mark.skipif(os.name != "nt", reason="Windows paths are case-insensitive")
def test_case_difference_is_accepted_on_windows(tmp_path):
    resolve_inside(str(tmp_path).upper() + "\\x.iso", str(tmp_path))


@pytest.fixture
def dirs(tmp_path):
    iso_dir, export_dir = tmp_path / "isos", tmp_path / "exports"
    with (
        patch("app.models.schemas.get_iso_dir", return_value=str(iso_dir)),
        patch("app.models.schemas.get_export_dir", return_value=str(export_dir)),
    ):
        yield iso_dir, export_dir


def test_request_schemas_enforce_directories(dirs, tmp_path):
    iso_dir, export_dir = dirs
    vm_id = uuid.uuid4()
    outside = str(tmp_path / "x")

    ISOAttachRequest(vm_id=vm_id, iso_path=str(iso_dir / "a.iso"))
    AIAttachISO(action="attach_iso", vm_id=vm_id, iso_path=str(iso_dir / "a.iso"))
    OVAExportRequest(vm_id=vm_id, output_path=str(export_dir / "a.ova"))
    OVAImportRequest(source_path=str(export_dir / "a.ova"), name="imported")

    for build in (
        lambda: ISOAttachRequest(vm_id=vm_id, iso_path=outside + ".iso"),
        lambda: AIAttachISO(action="attach_iso", vm_id=vm_id, iso_path=outside + ".iso"),
        lambda: OVAExportRequest(vm_id=vm_id, output_path=outside + ".ova"),
        lambda: OVAImportRequest(source_path=outside + ".ova", name="imported"),
    ):
        with pytest.raises(ValidationError):
            build()


def test_export_outside_directory_returns_422(dirs, tmp_path):
    app = FastAPI()
    app.include_router(vm_router, prefix="/api/v1/vm")
    app.dependency_overrides[get_current_user] = lambda: None

    with patch("app.services.vm_service.export_ova") as export:
        resp = TestClient(app).post(
            "/api/v1/vm/export",
            json={"vm_id": str(uuid.uuid4()), "output_path": str(tmp_path / "evil.ova")},
        )

    assert resp.status_code == 422
    export.assert_not_called()
