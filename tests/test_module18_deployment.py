"""Unit and integration tests for Module 18 (Deployment & OSS Storage)."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest
from app.storage.oss_client import OSSClient


def test_oss_client_initialization():
    """Verify that the OSSClient constructor instantiates with local directories ready."""
    client = OSSClient()
    assert client.local_assets_dir.exists()
    assert client.local_assets_dir.is_dir()


def test_oss_client_local_fallback_upload():
    """Verify that uploading a temp file correctly triggers the local assets directory fallback."""
    client = OSSClient()
    
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(b"AgentSphere OS Local Asset Test content")
        tmp_name = tmp.name
        
    try:
        url = client.upload_file(tmp_name)
        # Expected fallback static URL
        filename = Path(tmp_name).name
        assert url == f"/static/assets/{filename}"
        
        # Verify the file was indeed copied to local assets
        copied_file = client.local_assets_dir / filename
        assert copied_file.exists()
        assert copied_file.read_text() == "AgentSphere OS Local Asset Test content"
        
        # Clean up copied file
        copied_file.unlink()
    finally:
        # Clean up temp file
        Path(tmp_name).unlink()


def test_oss_client_upload_non_existent_file_raises_error():
    """Verify that attempting to upload a missing file raises FileNotFoundError."""
    client = OSSClient()
    with pytest.raises(FileNotFoundError):
        client.upload_file("non_existent_file_path_12345.xyz")
