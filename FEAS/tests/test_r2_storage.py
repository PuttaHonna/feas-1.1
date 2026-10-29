"""
Unit tests for Cloudflare R2 Cloud Storage Integration
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.services.r2_storage_service import CloudflareR2Service, r2_service


def test_r2_service_unconfigured_defaults():
    """Verify that r2_service gracefully defaults to local fallback when no keys are present."""
    with patch.dict(os.environ, {}, clear=True):
        srv = CloudflareR2Service()
        assert not srv.is_configured()
        status = srv.get_status()
        assert status["is_configured"] is False
        assert status["active"] is False
        assert status["free_tier"]["storage_capacity"] == "10 GB Free Forever"


def test_r2_service_configured_mock():
    """Verify initialization and status when Cloudflare R2 credentials are provided."""
    env = {
        "R2_ACCOUNT_ID": "mock_acc_1234567890",
        "R2_ACCESS_KEY_ID": "mock_key_abcdefghij",
        "R2_SECRET_ACCESS_KEY": "mock_secret_xyz1234567890",
        "R2_BUCKET_NAME": "test-cctv-bucket",
        "R2_PUBLIC_URL": "https://media.feas-cctv.com",
    }
    with patch.dict(os.environ, env):
        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            mock_boto.return_value = mock_client

            srv = CloudflareR2Service()
            assert srv.is_configured()
            assert srv.bucket_name == "test-cctv-bucket"
            status = srv.get_status()
            assert status["is_configured"] is True
            assert status["has_public_url"] is True


def test_r2_upload_and_auto_clean(tmp_path: Path):
    """Verify file upload to R2 and local file cleanup."""
    env = {
        "R2_ACCOUNT_ID": "mock_acc_1234567890",
        "R2_ACCESS_KEY_ID": "mock_key_abcdefghij",
        "R2_SECRET_ACCESS_KEY": "mock_secret_xyz1234567890",
        "R2_BUCKET_NAME": "test-cctv-bucket",
        "R2_AUTO_CLEAN_LOCAL": "true",
    }
    with patch.dict(os.environ, env):
        with patch("boto3.client") as mock_boto:
            mock_client = MagicMock()
            mock_boto.return_value = mock_client

            srv = CloudflareR2Service()

            # Create dummy video and keyframe
            dummy_video = tmp_path / "test_annotated.mp4"
            dummy_video.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"A" * 1024)

            dummy_raw = tmp_path / "test_raw.mp4"
            dummy_raw.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"B" * 1024)

            dummy_kf = tmp_path / "kf_01.jpg"
            dummy_kf.write_bytes(b"\xff\xd8\xff\xe0" + b"C" * 512)

            res = srv.process_and_archive_cctv_run(
                case_id="CASE-TEST-001",
                evidence_id="EV-001",
                annotated_video_path=dummy_video,
                raw_video_path=dummy_raw,
                keyframe_paths=[dummy_kf]
            )

            assert res["cloud_active"] is True
            assert res["storage"] == "CLOUDFLARE_R2"
            mock_client.upload_file.assert_called()

            # Ensure local raw and annotated files were cleaned up to preserve container disk
            assert not dummy_video.exists()
            assert not dummy_raw.exists()

