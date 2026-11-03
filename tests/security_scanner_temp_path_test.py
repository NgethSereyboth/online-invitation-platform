"""The malware scanner must not derive its temp path from an upload name."""
import os
from pathlib import Path

import security_scanner_v54 as scanner


def test_scan_bytes_uses_a_fixed_suffix_and_removes_the_temp_file(monkeypatch):
    seen = {}

    def fake_scan_file(path):
        seen["path"] = path
        seen["exists_during_scan"] = os.path.exists(path)
        return {"clean": True, "message": "ok"}

    monkeypatch.setattr(scanner, "scan_file", fake_scan_file)
    result = scanner.scan_bytes(b"payload", "../../private-name.exe")

    assert result == {"clean": True, "message": "ok"}
    assert seen["exists_during_scan"] is True
    assert Path(seen["path"]).suffix == ".bin"
    assert "private-name" not in Path(seen["path"]).name
    assert not os.path.exists(seen["path"])
